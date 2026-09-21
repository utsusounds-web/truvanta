import uuid

from django.db import models


class Feature(models.Model):
    """A single gatable capability of the app (e.g. 'ai_addon',
    'multi_branch', 'advanced_reports'). This is the catalog you (the
    platform owner) manage from the admin panel — new paid features
    get added here first, then attached to one or more Plans.

    `key` is what application code checks against (see
    services.business_has_feature) — stable, never renamed once used.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=60, unique=True, help_text="Stable identifier checked in code, e.g. 'ai_addon'.")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, help_text="Inactive features are hidden from new Plans but existing grants still work.")
    lock_priority = models.IntegerField(
        default=100,
        help_text="Lower locks first. When a trial or subscription lapses and a grace period "
                   "is configured (see PlatformSettings), only the lowest-numbered features here "
                   "stay usable during it — everything else locks immediately. Purely an admin "
                   "ordering knob; it has no effect while rent mode is on or a plan/trial already "
                   "grants the feature outright.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.key


class Plan(models.Model):
    """A paid tier a Business can subscribe to. Editable entirely from
    the admin panel — create/retire plans, change price, and change
    which Features they unlock, all without a code deploy.
    """

    INTERVAL_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.CharField(max_length=500, blank=True)

    price_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="In the currency below, e.g. 5000.00.")
    currency = models.CharField(max_length=8, default="NGN")
    billing_interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default="monthly")

    features = models.ManyToManyField(Feature, related_name="plans", blank=True)

    # Paystack "Plan" — created lazily the first time a business
    # subscribes to this Plan, so editing price/name here before that
    # point never touches Paystack. Once paystack_plan_code is set,
    # changing price_amount/billing_interval here will NOT retroactively
    # change the Paystack-side plan (Paystack plans are immutable on
    # amount); create a new Plan instead if pricing changes.
    paystack_plan_code = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True, help_text="Inactive plans are hidden from the upgrade page but existing subscribers keep their access.")
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "price_amount"]

    def __str__(self):
        return f"{self.name} ({self.price_amount} {self.currency}/{self.billing_interval})"

    @property
    def amount_kobo(self) -> int:
        """Paystack amounts are in the currency's smallest unit (kobo for NGN)."""
        return int(self.price_amount * 100)


class Subscription(models.Model):
    """A Business's relationship to a Plan, mirroring Paystack's
    subscription lifecycle. One row per Business — history of past
    subscriptions is kept in BillingEvent, not by multiplying rows here.
    """

    STATUS_CHOICES = [
        ("none", "No subscription"),
        ("trialing", "Free trial"),
        ("pending", "Pending first payment"),
        ("active", "Active"),
        ("past_due", "Payment failed / past due"),
        ("canceled", "Canceled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField("tenants.Business", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="none")

    paystack_customer_code = models.CharField(max_length=100, blank=True)
    paystack_subscription_code = models.CharField(max_length=100, blank=True)
    paystack_email_token = models.CharField(
        max_length=200, blank=True,
        help_text="Required by Paystack to manage/cancel the subscription via API.",
    )

    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.business.name}: {self.plan.name if self.plan else 'no plan'} [{self.status}]"

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class FeatureOverride(models.Model):
    """A manual, per-business grant or revoke of a single Feature —
    independent of (and takes priority over) whatever the business's
    Subscription plan includes. This is the platform-admin "activate
    this feature for this user" control: comp a feature for free,
    give a trial, or forcibly disable something regardless of plan.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="feature_overrides")
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name="overrides")
    is_enabled = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True, help_text="Why this override exists, e.g. 'trial until launch', 'comped for beta tester'.")
    granted_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Leave blank for a permanent override.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("business", "feature")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.business.name}: {self.feature.key} = {self.is_enabled}"


class BillingEvent(models.Model):
    """Immutable log of every Paystack webhook received, processed or
    not. Kept for debugging failed payments/disputes — never edited.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_events")
    event_type = models.CharField(max_length=100)
    paystack_reference = models.CharField(max_length=100, blank=True)
    raw_payload = models.JSONField(default=dict)
    processed_ok = models.BooleanField(default=False)
    error = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"
