import os
import uuid

from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models

from apps.core.models import TimeStampedModel


def business_logo_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"business_logos/{instance.id}/logo.{ext}"


class Business(TimeStampedModel):
    """A tenant. All data in the system is ultimately scoped to a Business.

    Branding fields here (logo, name, address, phone, receipt footer,
    currency, timezone) are the single source of truth for every
    generated document — receipts, invoices, quotations, statements,
    purchase orders, reports. Document generators must pull from this
    model rather than hard-coding or duplicating business info, so a
    logo/name change instantly applies everywhere.
    """

    BUSINESS_TYPE_CHOICES = [
        ("retail", "Retail / Shop"),
        ("wholesale", "Wholesale"),
        ("provisions", "Provision Store"),
        ("boutique", "Boutique"),
        ("pharmacy", "Pharmacy"),
        ("restaurant", "Restaurant"),
        ("kiosk", "Kiosk"),
        ("supermarket", "Supermarket"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    signup_code = models.CharField(
        max_length=12, unique=True, db_index=True,
        help_text="Given to staff so they can register their own location as a branch of this "
                   "business, pending your approval. Owner/admin can regenerate it any time, "
                   "which immediately invalidates the old code.",
    )
    support_access_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="While set and in the future, Truvanta platform staff may log into this "
                   "business to help with support — only ever with the owner/admin explicitly "
                   "granting it here first, for a limited time, and revocable instantly.",
    )

    # --- Scheduled deletion (GDPR / account-closure requests) ---
    # Deliberately a two-step, delayed process — never an instant
    # delete button. Staff schedule it (typing the business's exact
    # name to confirm), which freezes the account and starts a grace
    # window; only after that window has actually passed can staff
    # execute the real, irreversible deletion — with a second name
    # confirmation at that point too. See AdminScheduleDeletionView /
    # AdminExecutePurgeView in apps.billing.views.
    pending_deletion_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Once this passes, the business becomes eligible for permanent deletion — but "
                   "deletion still never happens automatically, staff must explicitly execute it.",
    )
    deletion_requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    business_type = models.CharField(max_length=30, choices=BUSINESS_TYPE_CHOICES, default="retail")

    # --- Branding: used on every generated document ---
    logo = models.ImageField(
        upload_to=business_logo_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg", "webp", "svg"])],
        help_text="Displayed on every receipt, invoice, statement, and report header.",
    )
    address = models.CharField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    theme_color = models.CharField(
        max_length=7, blank=True, default="#E3A635",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a hex color like #E3A635.")],
        help_text="Hex accent color (e.g. #E3A635) applied across the app's sidebar and highlights "
                   "for this business — owner/admin editable from Settings, no code change needed.",
    )
    receipt_header_note = models.CharField(
        max_length=255, blank=True,
        help_text="Optional line shown under the business name on documents, e.g. a tagline.",
    )
    receipt_footer_note = models.CharField(
        max_length=255, blank=True, default="Thank you for your patronage!",
        help_text="Owner-editable line at the bottom of receipts, e.g. return policy.",
    )

    currency_code = models.CharField(max_length=8, default="NGN")
    timezone = models.CharField(max_length=64, default="Africa/Lagos")

    # --- Tax ---
    default_tax_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Applied automatically at POS checkout when set. Leave blank for no default tax.",
    )

    # --- Notification delivery (WhatsApp + Gmail) ---
    notification_whatsapp_number = models.CharField(
        max_length=32, blank=True,
        help_text="E.164 format, e.g. +2348012345678. Where critical/important alerts are sent via WhatsApp.",
    )
    notification_email = models.EmailField(
        blank=True, help_text="Where alerts are sent via email. Defaults to the business email if blank.",
    )

    # --- AI features ---
    ai_addon_enabled = models.BooleanField(
        default=False,
        help_text="AI features (voice bookkeeping, receipt scanning, 'ask my business') are a paid "
                   "add-on, gated by this flag once billing/subscription is wired up.",
    )

    # --- Payments (this business's own Paystack account, for accepting
    # customer payments in POS/checkout — separate from the platform's
    # own Paystack keys used to bill for the AI add-on, see PlatformSettings) ---
    paystack_public_key = models.CharField(max_length=200, blank=True)
    paystack_secret_key = models.CharField(
        max_length=200, blank=True,
        help_text="Stored as-is for now; in a production deployment this should be encrypted at rest "
                   "(e.g. via django-encrypted-model-fields) rather than plain text.",
    )

    # --- Owner Away Mode (spec section 11) ---
    # When enabled, discounts/refunds/price changes above these
    # thresholds trigger an immediate critical notification instead of
    # only showing up in the (up-to-7-day-delayed) risk scan — meant
    # for exactly the situation the name describes: the owner isn't
    # physically present to notice in the moment.
    away_mode_enabled = models.BooleanField(default=False)
    away_mode_discount_threshold_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="A discount above this % of a sale line's value triggers an immediate alert.",
    )
    away_mode_refund_threshold_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="A refund above this amount triggers an immediate alert (refunds already require approval regardless).",
    )
    away_mode_price_change_threshold_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="A cost-price change above this % triggers an immediate alert.",
    )

    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="owned_businesses",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def branding_context(self) -> dict:
        """Common dict every document template/renderer should use.

        Centralizing this means a new document type (e.g. a supplier
        statement added next sprint) automatically gets correct,
        consistent branding without re-deriving these fields.
        """
        return {
            "business_name": self.name,
            "logo_url": self.logo.url if self.logo else None,
            "address": self.address,
            "phone_number": self.phone_number,
            "email": self.email,
            "header_note": self.receipt_header_note,
            "footer_note": self.receipt_footer_note,
            "currency_code": self.currency_code,
        }


class Branch(TimeStampedModel):
    """A physical location belonging to a Business.

    A branch can override the logo/address/phone shown on its own
    documents (e.g. a different street address per outlet); anything
    left blank falls back to the parent Business's branding.
    """

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    parent_branch = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_branches",
        help_text="For businesses with many locations: set this to make a branch a 'mini-branch' "
                   "under a main one, for organization. A branch with no parent is a main branch. "
                   "Data access isn't restricted by this hierarchy — it's organizational, not a permission boundary.",
    )
    logo = models.ImageField(
        upload_to=business_logo_path, null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["png", "jpg", "jpeg", "webp", "svg"])],
        help_text="Overrides the business logo on this branch's documents. Leave blank to inherit.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("business", "name")]
        ordering = ["business", "name"]

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    @property
    def branding_context(self) -> dict:
        ctx = self.business.branding_context
        if self.logo:
            ctx["logo_url"] = self.logo.url
        if self.address:
            ctx["address"] = self.address
        if self.phone_number:
            ctx["phone_number"] = self.phone_number
        ctx["branch_name"] = self.name
        return ctx


class BranchJoinRequest(TimeStampedModel):
    """Someone with a business's signup code asking to register their
    own location as a new branch of it. Stays pending until the
    owner/admin approves (which creates the Branch + a minimum-trust
    Membership for them) or rejects it. The requester never gets any
    access to the business until approved — this is the only path
    for a new branch to be created by anyone other than the owner/admin
    directly on the Branches page.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="branch_join_requests")
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="branch_join_requests",
    )
    branch_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Set once approved — the branch this request resulted in.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requested_by.email} → {self.business.name} ({self.branch_name}) [{self.status}]"
