"""Paystack recurring-subscription integration, plus the single
function (business_has_feature) the rest of the app calls to decide
whether a business can use a gated feature right now.

Credentials are resolved from PlatformSettings first (editable by
staff via the API/frontend, no redeploy needed) and fall back to
.env, matching the pattern already used in apps/notifications/services.py.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import PlatformSettings

from .models import BillingEvent, Feature, FeatureOverride, Plan, Subscription

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _secret_key() -> str:
    platform = PlatformSettings.load()
    key = platform.platform_paystack_secret_key or getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not key:
        raise PaystackError(
            "Paystack is not configured (set it in Settings > Platform Integrations, "
            "or PAYSTACK_SECRET_KEY in .env)."
        )
    return key


def _headers() -> dict:
    return {"Authorization": f"Bearer {_secret_key()}", "Content-Type": "application/json"}


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        resp = requests.request(method, f"{PAYSTACK_BASE_URL}{path}", headers=_headers(), timeout=15, **kwargs)
    except requests.RequestException as e:
        raise PaystackError(f"Paystack request failed: {e}") from e
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not data.get("status", True):
        raise PaystackError(data.get("message", f"Paystack API error {resp.status_code}"))
    return data


# --- Plan sync -------------------------------------------------------

def ensure_paystack_plan(plan: Plan) -> str:
    """Create the recurring Plan on Paystack's side the first time it's
    needed, and cache the code. Paystack plans are effectively
    immutable on amount/interval once created — if you need to change
    pricing, create a new Plan row instead of editing this one.
    """
    if plan.paystack_plan_code:
        return plan.paystack_plan_code
    data = _request(
        "POST", "/plan",
        json={
            "name": plan.name,
            "amount": plan.amount_kobo,
            # Paystack's own interval vocabulary doesn't match ours
            # 1:1 — it has no "yearly", only "annually". Passing
            # "yearly" straight through would have been rejected by
            # Paystack's API the first time anyone tried to create a
            # yearly plan.
            "interval": {"daily": "daily", "weekly": "weekly", "monthly": "monthly", "yearly": "annually"}[plan.billing_interval],
            "currency": plan.currency,
        },
    )
    code = data["data"]["plan_code"]
    plan.paystack_plan_code = code
    plan.save(update_fields=["paystack_plan_code"])
    return code


# --- Starting a subscription ------------------------------------------

def initialize_subscription_checkout(business, plan: Plan, email: str, callback_url: str) -> str:
    """Starts (or restarts/switches) a business's subscription to `plan`.
    Returns the Paystack checkout URL the frontend should redirect the
    user to. On successful payment, Paystack auto-creates the
    subscription and fires webhooks that finish activation
    (see handle_webhook_event) — nothing else needs to happen here.
    """
    plan_code = ensure_paystack_plan(plan)
    data = _request(
        "POST", "/transaction/initialize",
        json={
            "email": email,
            "amount": plan.amount_kobo,
            "plan": plan_code,
            "callback_url": callback_url,
            "metadata": {"business_id": str(business.id), "plan_id": str(plan.id)},
        },
    )
    return data["data"]["authorization_url"]


def cancel_subscription(subscription: Subscription) -> None:
    if not subscription.paystack_subscription_code or not subscription.paystack_email_token:
        # Never actually activated via Paystack (e.g. admin-granted) — just cancel locally.
        subscription.status = "canceled"
        subscription.cancel_at_period_end = False
        subscription.save(update_fields=["status", "cancel_at_period_end"])
        return
    _request(
        "POST", "/subscription/disable",
        json={
            "code": subscription.paystack_subscription_code,
            "token": subscription.paystack_email_token,
        },
    )
    subscription.cancel_at_period_end = True
    subscription.save(update_fields=["cancel_at_period_end"])


# --- Webhooks -----------------------------------------------------------

def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if not signature:
        return False
    computed = hmac.new(_secret_key().encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)


@transaction.atomic
def handle_webhook_event(event: dict) -> None:
    """Dispatch a verified Paystack webhook payload. Every event is
    logged to BillingEvent (processed or not) before/after handling,
    so a bug here is debuggable from the admin panel rather than
    silently losing a payment update.
    """
    event_type = event.get("event", "")
    data = event.get("data", {}) or {}
    metadata = data.get("metadata") or {}
    business_id = metadata.get("business_id")
    reference = data.get("reference", "") or data.get("subscription_code", "")

    log = BillingEvent.objects.create(
        business_id=business_id or None,
        event_type=event_type,
        paystack_reference=reference,
        raw_payload=event,
    )

    try:
        if event_type == "charge.success" and business_id:
            _activate_from_charge(business_id, data)
        elif event_type == "subscription.create":
            _attach_subscription_codes(data)
        elif event_type in ("subscription.disable", "subscription.not_renew"):
            _deactivate_subscription(data)
        elif event_type == "invoice.payment_failed":
            _mark_past_due(data)
        # Other event types (invoice.create, invoice.update, etc.) are
        # logged above but need no state change.
        log.processed_ok = True
    except Exception as e:  # noqa: BLE001 - log and move on, never 500 the webhook
        log.error = str(e)[:500]
        logger.exception("Failed processing Paystack webhook %s", event_type)
    log.save(update_fields=["processed_ok", "error"])


def _activate_from_charge(business_id: str, data: dict) -> None:
    from apps.tenants.models import Business
    metadata = data.get("metadata") or {}
    plan_id = metadata.get("plan_id")
    if not plan_id:
        return
    business = Business.objects.get(pk=business_id)
    plan = Plan.objects.get(pk=plan_id)
    sub, _ = Subscription.objects.get_or_create(business=business)
    sub.plan = plan
    sub.status = "active"
    sub.paystack_customer_code = (data.get("customer") or {}).get("customer_code", sub.paystack_customer_code)
    # Interim period-end estimate; subscription.create webhook (fired
    # right after) fills in the precise value from Paystack.
    days = {"daily": 1, "weekly": 7, "monthly": 31, "yearly": 365}[plan.billing_interval]
    sub.current_period_end = timezone.now() + timedelta(days=days)
    sub.cancel_at_period_end = False
    sub.save()


def _attach_subscription_codes(data: dict) -> None:
    customer_code = (data.get("customer") or {}).get("customer_code")
    if not customer_code:
        return
    sub = Subscription.objects.filter(paystack_customer_code=customer_code).order_by("-updated_at").first()
    if not sub:
        return
    sub.paystack_subscription_code = data.get("subscription_code", sub.paystack_subscription_code)
    sub.paystack_email_token = data.get("email_token", sub.paystack_email_token)
    next_payment = data.get("next_payment_date")
    if next_payment:
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(next_payment)
        if parsed:
            sub.current_period_end = parsed
    sub.status = "active"
    sub.save()


def _deactivate_subscription(data: dict) -> None:
    code = data.get("subscription_code")
    if not code:
        return
    Subscription.objects.filter(paystack_subscription_code=code).update(status="canceled")


def _mark_past_due(data: dict) -> None:
    sub_code = (data.get("subscription") or {}).get("subscription_code") or data.get("subscription_code")
    if not sub_code:
        return
    Subscription.objects.filter(paystack_subscription_code=sub_code).update(status="past_due")


# --- Feature access check ------------------------------------------------

def business_has_feature(business_id, feature_key: str) -> bool:
    """The single choke point every feature-gated view should call.

    Order of precedence:
    1. Rent Mode OFF (PlatformSettings.rent_mode_enabled) — everything
       is unlocked for everyone. This is the deliberate kill switch:
       flip it off during a demo/free period, on when you're ready to
       charge, with nothing else to change.
    2. An explicit FeatureOverride always wins next — lets you comp or
       forcibly revoke a feature for one business regardless of plan.
    3. An unexpired free trial (Subscription.status='trialing') grants
       every feature, not just whatever one plan includes — the whole
       point of a trial is to show a new business the full power of
       what they'd be paying for, not a watered-down preview. Once the
       trial's current_period_end passes, this stops applying on its
       own (the status field itself doesn't need to be flipped by a
       background job — see BusinessCreateView for where the trial is
       actually started).
    4. Otherwise fall back to whatever the business's active
       Subscription plan includes. If there is no active plan but one
       lapsed recently enough to still be inside an admin-configured
       grace window (PlatformSettings.trial_grace_days), the handful
       of features an admin has marked lowest lock_priority stay
       usable until that window closes — see the grace-period check
       below. Nothing here ever blocks the features that were never
       feature-gated in the first place (core sales, expenses,
       customers, simple stock, basic reports) — those aren't behind
       HasFeature at all, so a business with no subscription and no
       trial can still run on Truvanta.
    """
    if not PlatformSettings.load().rent_mode_enabled:
        return True

    if not business_id:
        return False

    try:
        feature = Feature.objects.get(key=feature_key, is_active=True)
    except Feature.DoesNotExist:
        return False

    override = FeatureOverride.objects.filter(business_id=business_id, feature=feature).first()
    if override:
        if override.expires_at and override.expires_at < timezone.now():
            pass  # expired — fall through to plan check
        else:
            return override.is_enabled

    sub = Subscription.objects.filter(business_id=business_id).select_related("plan").first()
    if sub and sub.status == "trialing" and sub.current_period_end and sub.current_period_end > timezone.now():
        return True

    if not sub or sub.status != "active" or not sub.plan:
        # Not on a currently-active paid plan. Before fully locking
        # out, check whether the trial/subscription lapsed recently
        # enough to still be inside an admin-configured grace window —
        # and if so, whether this specific feature is ranked low
        # enough (lock_priority) to be one of the few that survive it.
        # Without this, every gated feature disappeared the instant a
        # trial ended, all at once, with no way for an admin to soften
        # that for anyone.
        if sub and sub.current_period_end:
            settings_row = PlatformSettings.load()
            grace_days = settings_row.trial_grace_days
            grace_count = settings_row.trial_grace_feature_count
            if grace_days > 0 and grace_count > 0:
                lapsed_at = sub.current_period_end
                grace_ends = lapsed_at + timedelta(days=grace_days)
                if lapsed_at < timezone.now() <= grace_ends:
                    protected_keys = set(
                        Feature.objects.filter(is_active=True)
                        .order_by("lock_priority", "name")
                        .values_list("key", flat=True)[:grace_count]
                    )
                    if feature_key in protected_keys:
                        return True
        return False
    return sub.plan.features.filter(pk=feature.pk).exists()
