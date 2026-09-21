import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import IsBusinessMember
from apps.tenants.models import Business
from apps.products.models import Product
from apps.customers.models import Customer
from apps.expenses.models import Expense
from apps.documents.models import VaultDocument
from apps.sales.models import Sale
from apps.suppliers.models import Supplier
from apps.audit.models import AuditLog
from apps.audit.services import log_action

from . import services
from .models import BillingEvent, Feature, FeatureOverride, Plan, Subscription
from .permissions import IsPlatformAdmin
from .serializers import (
    BillingEventSerializer,
    FeatureOverrideSerializer,
    FeatureSerializer,
    PlanSerializer,
    SubscribeRequestSerializer,
    SubscriptionSerializer,
)


# --- Business-facing: browse plans, manage own subscription ---------------

class PlanListView(generics.ListAPIView):
    """Public pricing list — every authenticated user can see what's
    on offer, regardless of business membership."""
    serializer_class = PlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Plan.objects.filter(is_active=True).prefetch_related("features")


class MySubscriptionView(generics.RetrieveAPIView):
    """The current business's own subscription status + unlocked features."""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsBusinessMember]

    def get_object(self):
        sub, _ = Subscription.objects.get_or_create(business_id=self.request.business_id)
        return sub


def _require_owner_or_admin(request):
    role = request.membership.role.system_role
    if role not in ("owner", "admin"):
        raise PermissionDenied("Only the business owner or an admin can manage billing.")


class SubscribeView(APIView):
    """Starts (or switches) the business's subscription to a Plan.
    Returns a Paystack checkout URL for the frontend to redirect to;
    activation itself happens via the webhook once payment succeeds."""
    permission_classes = [IsBusinessMember]
    throttle_scope = "billing"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        _require_owner_or_admin(request)
        serializer = SubscribeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = Business.objects.get(pk=request.business_id)
        try:
            plan = Plan.objects.get(pk=serializer.validated_data["plan_id"], is_active=True)
        except Plan.DoesNotExist:
            raise ValidationError({"plan_id": "Plan not found or no longer available."})

        try:
            checkout_url = services.initialize_subscription_checkout(
                business=business,
                plan=plan,
                email=request.user.email,
                callback_url=serializer.validated_data["callback_url"],
            )
        except services.PaystackError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        Subscription.objects.update_or_create(business=business, defaults={"status": "pending"})
        return Response({"checkout_url": checkout_url})


class CancelSubscriptionView(APIView):
    permission_classes = [IsBusinessMember]
    throttle_scope = "billing"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        _require_owner_or_admin(request)
        try:
            sub = Subscription.objects.get(business_id=request.business_id)
        except Subscription.DoesNotExist:
            raise ValidationError("No subscription to cancel.")
        try:
            services.cancel_subscription(sub)
        except services.PaystackError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(SubscriptionSerializer(sub).data)


# --- Webhook (public, Paystack calls this directly) ------------------------

@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    """No auth — Paystack calls this server-to-server. Authenticity is
    verified via the signature header instead (see services.verify_webhook_signature).
    Scoped separately from the general anon rate so retry bursts from
    Paystack's side don't compete with real anonymous traffic sharing
    the same limit bucket."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "webhook"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        signature = request.headers.get("X-Paystack-Signature", "")
        raw_body = request.body
        if not services.verify_webhook_signature(raw_body, signature):
            return Response({"detail": "Invalid signature."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            event = json.loads(raw_body)
        except (json.JSONDecodeError, TypeError):
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)
        services.handle_webhook_event(event)
        return Response({"received": True})


# --- Platform admin: manage the catalog, view/override businesses ---------

class FeatureAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdmin]
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer


class PlanAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdmin]
    queryset = Plan.objects.all().prefetch_related("features")
    serializer_class = PlanSerializer


class AdminBusinessLookupView(APIView):
    """Lightweight {id, name} list of every business, for the admin
    panel's 'grant this feature to...' picker. Kept minimal and
    separate from the full BusinessSerializer (billing admin has no
    reason to see/edit branding, credentials, etc.)."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        businesses = Business.objects.order_by("name").values(
            "id", "name", "is_active", "support_access_expires_at", "pending_deletion_at",
        )
        return Response(list(businesses))


class AdminSubscriptionListView(generics.ListAPIView):
    """Every business's subscription status, for the platform-admin
    dashboard — see who's on what plan, who's past due, at a glance."""
    permission_classes = [IsPlatformAdmin]
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.select_related("business", "plan").prefetch_related("plan__features")


class AdminUsageAnalyticsView(APIView):
    """'How many people use the app' — real counts, not vanity
    metrics: businesses, users, weekly/monthly active users, which
    businesses are actually transacting vs. dormant, and subscription
    mix by plan. See platform_analytics.py for exactly what's computed
    and why each figure is defined the way it is."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from . import platform_analytics
        return Response(platform_analytics.platform_usage_summary())


class AdminActivateSubscriptionView(APIView):
    """Lets the platform admin directly put a business on a plan —
    for an offline/manual payment (bank transfer, cash, a sales-
    assisted deal), a comp, or correcting something Paystack's webhook
    missed. This bypasses Paystack entirely: it's the platform admin's
    own authority to say 'this business is on this plan', the same
    authority a human support rep at any SaaS company has to manually
    fix or grant a subscription. Every activation is logged as a
    BillingEvent (event_type='admin_manual_activation') so there's a
    record distinguishing a real payment from an admin action, exactly
    the kind of distinction that matters if it's ever questioned later.
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta

        business_id = request.data.get("business")
        plan_id = request.data.get("plan")
        if not business_id or not plan_id:
            return Response({"detail": "business and plan are required."}, status=400)

        business = Business.objects.get(pk=business_id)
        plan = Plan.objects.get(pk=plan_id)

        days = {"daily": 1, "weekly": 7, "monthly": 31, "yearly": 365}[plan.billing_interval]
        period_days = int(request.data.get("period_days", days))

        sub, _ = Subscription.objects.get_or_create(business=business)
        sub.plan = plan
        sub.status = "active"
        sub.current_period_end = timezone.now() + timedelta(days=period_days)
        sub.cancel_at_period_end = False
        sub.save()

        BillingEvent.objects.create(
            business=business, event_type="admin_manual_activation", processed_ok=True,
            raw_payload={
                "plan_id": str(plan.id), "plan_name": plan.name, "billing_interval": plan.billing_interval,
                "period_days": period_days, "activated_by": request.user.email,
                "note": request.data.get("note", ""),
            },
        )
        log_action(
            business=business, actor=request.user, action="other", target=sub,
            new_value={"plan": plan.name, "period_days": period_days, "status": "active"},
            reason=f"Platform admin: manually activated subscription ({plan.name}, {period_days} days).",
        )
        return Response(SubscriptionSerializer(sub).data, status=200)


class AdminTenantUsageView(APIView):
    """Platform staff only: approximate storage and data-volume usage
    for one business, computed on demand (not for the whole business
    list at once — summing real file sizes on disk isn't cheap, so
    this only runs when specifically asked for one tenant)."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request, business_id):
        business = generics.get_object_or_404(Business, id=business_id)

        def file_bytes(field_file):
            try:
                return field_file.size if field_file else 0
            except (OSError, ValueError):
                return 0  # file referenced in DB but missing on disk — don't crash the report over it

        media_bytes = file_bytes(business.logo)
        for branch in business.branches.all():
            media_bytes += file_bytes(branch.logo)
        for product in Product.objects.filter(business=business).only("image"):
            media_bytes += file_bytes(product.image)
        for customer in Customer.objects.filter(business=business).only("photo"):
            media_bytes += file_bytes(customer.photo)
        for expense in Expense.objects.filter(business=business).only("receipt_image"):
            media_bytes += file_bytes(expense.receipt_image)
        for doc in VaultDocument.objects.filter(business=business).only("file"):
            media_bytes += file_bytes(doc.file)

        row_counts = {
            "products": Product.objects.filter(business=business).count(),
            "sales": Sale.objects.filter(business=business).count(),
            "customers": Customer.objects.filter(business=business).count(),
            "suppliers": Supplier.objects.filter(business=business).count(),
            "documents": VaultDocument.objects.filter(business=business).count(),
            "audit_log_entries": AuditLog.objects.filter(business=business).count(),
        }

        return Response({
            "business_id": str(business.id),
            "business_name": business.name,
            "media_bytes": media_bytes,
            "row_counts": row_counts,
            "total_rows": sum(row_counts.values()),
        })


class AdminExtendTrialView(APIView):
    """Extends a business's current period end (trial or paid) by N
    days without changing its plan or status — the "give them a bit
    more time" button, distinct from AdminActivateSubscriptionView
    which puts them on a specific plan."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta

        business_id = request.data.get("business")
        days = int(request.data.get("days", 7))
        if not business_id:
            return Response({"detail": "business is required."}, status=400)
        if not (1 <= days <= 365):
            return Response({"detail": "days must be between 1 and 365."}, status=400)

        business = Business.objects.get(pk=business_id)
        sub, _ = Subscription.objects.get_or_create(business=business)
        base = sub.current_period_end if sub.current_period_end and sub.current_period_end > timezone.now() else timezone.now()
        sub.current_period_end = base + timedelta(days=days)
        sub.save(update_fields=["current_period_end"])

        BillingEvent.objects.create(
            business=business, event_type="admin_trial_extension", processed_ok=True,
            raw_payload={
                "days_added": days, "new_period_end": sub.current_period_end.isoformat(),
                "extended_by": request.user.email,
            },
        )
        log_action(
            business=business, actor=request.user, action="other", target=sub,
            new_value={"days_added": days, "new_period_end": sub.current_period_end.isoformat()},
            reason=f"Platform admin: extended subscription period by {days} day(s).",
        )
        return Response(SubscriptionSerializer(sub).data, status=200)


class AdminScheduleDeletionView(APIView):
    """Step 1 of 2 for permanently deleting a business's data (GDPR /
    account-closure requests). Requires typing the business's exact
    name to confirm — never a single click. Freezes the account
    immediately and starts a grace window; nothing is actually
    deleted until AdminExecutePurgeView is separately called after
    that window passes, with its own name confirmation too."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta

        business_id = request.data.get("business")
        confirm_name = (request.data.get("confirm_name") or "").strip()
        days = int(request.data.get("grace_days", 7))
        business = generics.get_object_or_404(Business, id=business_id)

        if confirm_name != business.name:
            return Response(
                {"detail": "The name you typed doesn't match the business's exact name."}, status=400,
            )

        business.pending_deletion_at = timezone.now() + timedelta(days=max(1, min(days, 30)))
        business.deletion_requested_by = request.user
        business.is_active = False
        business.save(update_fields=["pending_deletion_at", "deletion_requested_by", "is_active"])

        BillingEvent.objects.create(
            business=business, event_type="admin_schedule_deletion", processed_ok=True,
            raw_payload={
                "scheduled_by": request.user.email,
                "eligible_from": business.pending_deletion_at.isoformat(),
            },
        )
        log_action(
            business=business, actor=request.user, action="other", target=business,
            new_value={"pending_deletion_at": business.pending_deletion_at.isoformat(), "grace_days": days},
            reason="Platform admin: scheduled this account for deletion.",
        )
        return Response({"id": str(business.id), "pending_deletion_at": business.pending_deletion_at})


class AdminCancelDeletionView(APIView):
    """The undo button, usable any time before the actual purge —
    clears the schedule and unfreezes the account."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        business_id = request.data.get("business")
        business = generics.get_object_or_404(Business, id=business_id)
        business.pending_deletion_at = None
        business.deletion_requested_by = None
        business.is_active = True
        business.save(update_fields=["pending_deletion_at", "deletion_requested_by", "is_active"])

        BillingEvent.objects.create(
            business=business, event_type="admin_cancel_deletion", processed_ok=True,
            raw_payload={"cancelled_by": request.user.email},
        )
        log_action(
            business=business, actor=request.user, action="other", target=business,
            reason="Platform admin: cancelled scheduled deletion.",
        )
        return Response({"id": str(business.id), "pending_deletion_at": None})


class AdminExecutePurgeView(APIView):
    """Step 2 of 2 — the actual, irreversible deletion. Only works
    once the grace window from step 1 has genuinely passed, and
    requires typing the business's exact name again, separately from
    the original scheduling confirmation."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from django.utils import timezone

        business_id = request.data.get("business")
        confirm_name = (request.data.get("confirm_name") or "").strip()
        business = generics.get_object_or_404(Business, id=business_id)

        if not business.pending_deletion_at:
            return Response({"detail": "This business isn't scheduled for deletion."}, status=400)
        if business.pending_deletion_at > timezone.now():
            return Response(
                {"detail": f"The grace window hasn't passed yet (eligible from {business.pending_deletion_at.isoformat()})."},
                status=400,
            )
        if confirm_name != business.name:
            return Response(
                {"detail": "The name you typed doesn't match the business's exact name."}, status=400,
            )

        name_snapshot, id_snapshot = business.name, str(business.id)
        # Recorded with business=None deliberately — the business row
        # itself is about to be gone, so nothing can hold a live FK to
        # it after this. Everything needed to identify what was
        # deleted and by whom lives in raw_payload instead.
        BillingEvent.objects.create(
            business=None, event_type="admin_execute_purge", processed_ok=True,
            raw_payload={
                "deleted_business_id": id_snapshot, "deleted_business_name": name_snapshot,
                "purged_by": request.user.email,
            },
        )
        # Also business=None here, for the same cascade-delete reason as
        # BillingEvent above: AuditLog.business is a real FK and would
        # delete this very row the instant business.delete() runs below
        # if it pointed at the business being purged.
        log_action(
            business=None, actor=request.user, action="other",
            new_value={"deleted_business_id": id_snapshot, "deleted_business_name": name_snapshot},
            reason=f"Platform admin: permanently deleted all data for '{name_snapshot}'.",
        )
        business.delete()
        return Response({"deleted": True, "business_id": id_snapshot, "business_name": name_snapshot})


class AdminFreezeAccountView(APIView):
    """Immediately blocks every member of a business from using the
    app (Business.is_active gates login/access) — for suspected fraud,
    non-payment, or a support escalation. Reversible any time by the
    same endpoint with active=true."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        business_id = request.data.get("business")
        active = bool(request.data.get("active", False))
        if not business_id:
            return Response({"detail": "business is required."}, status=400)

        business = Business.objects.get(pk=business_id)
        business.is_active = active
        business.save(update_fields=["is_active"])

        BillingEvent.objects.create(
            business=business, event_type="admin_freeze" if not active else "admin_unfreeze",
            processed_ok=True,
            raw_payload={"frozen": not active, "actioned_by": request.user.email},
        )
        log_action(
            business=business, actor=request.user, action="other", target=business,
            new_value={"is_active": active},
            reason=f"Platform admin: {'unfroze' if active else 'froze'} this account.",
        )
        return Response({"id": str(business.id), "is_active": business.is_active})


class AdminBroadcastNotificationView(APIView):
    """Post a notification into every (or a filtered set of) business's
    own notification feed — the platform admin equivalent of an
    announcement banner. Reuses apps.notifications.services.notify,
    the exact same mechanism a business's own automated alerts use, so
    a broadcast shows up exactly like any other notification (and
    still respects each business's own WhatsApp/email delivery
    settings) rather than being a separate, bolted-on channel.
    """
    permission_classes = [IsPlatformAdmin]
    throttle_scope = "billing"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        from apps.notifications.services import notify

        title = request.data.get("title", "").strip()
        message = request.data.get("message", "").strip()
        level = request.data.get("level", "info")
        target = request.data.get("target", "all")  # "all" | "active_subscribers" | "specific"
        business_ids = request.data.get("business_ids") or []

        if not title or not message:
            return Response({"detail": "title and message are required."}, status=400)
        if level not in ("critical", "important", "info"):
            return Response({"detail": "level must be critical, important, or info."}, status=400)

        if target == "specific":
            businesses = Business.objects.filter(id__in=business_ids)
        elif target == "active_subscribers":
            businesses = Business.objects.filter(subscription__status="active")
        else:
            businesses = Business.objects.all()

        sent_count = 0
        for business in businesses:
            notify(business=business, level=level, title=title, message=message)
            sent_count += 1

        log_action(
            business=None, actor=request.user, action="other",
            new_value={"title": title, "level": level, "target": target, "business_ids": business_ids, "sent_to_businesses": sent_count},
            reason=f"Platform admin: broadcast notification sent to {sent_count} business(es) — \"{title}\".",
        )
        return Response({"sent_to_businesses": sent_count})


class FeatureOverrideAdminViewSet(viewsets.ModelViewSet):
    """Grant or revoke a specific feature for a specific business,
    regardless of their subscription — the "activate this for a user"
    control, for comps, trials, or manual enforcement."""
    permission_classes = [IsPlatformAdmin]
    queryset = FeatureOverride.objects.select_related("business", "feature", "granted_by")
    serializer_class = FeatureOverrideSerializer
    filterset_fields = ["business", "feature", "is_enabled"]

    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)


class BillingEventAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only webhook log for debugging payment issues, plus a
    replay action for a failed one — re-runs the exact same handling
    logic against the originally-received payload, so a transient
    failure (a bug since fixed, a business that didn't exist yet at
    the time) can be manually resolved without waiting for Paystack
    to retry on its own schedule."""
    permission_classes = [IsPlatformAdmin]
    queryset = BillingEvent.objects.select_related("business")
    serializer_class = BillingEventSerializer
    filterset_fields = ["business", "event_type", "processed_ok"]

    @action(detail=True, methods=["post"])
    def replay(self, request, pk=None):
        log = self.get_object()
        services.handle_webhook_event(log.raw_payload)
        # handle_webhook_event always creates a fresh BillingEvent row
        # for the attempt (matching how a real Paystack retry would
        # look in the log) — it never mutates history in place, since
        # BillingEvent rows are meant to be an immutable trail.
        latest = BillingEvent.objects.filter(
            paystack_reference=log.paystack_reference, event_type=log.event_type,
        ).order_by("-created_at").first()
        return Response(BillingEventSerializer(latest).data)
