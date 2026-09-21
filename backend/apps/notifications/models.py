from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TenantScopedModel


class Notification(TenantScopedModel):
    """A record of something the owner was (or should be) told about,
    and whether it actually got delivered on each channel. Kept even
    when delivery fails so the in-app notification list is always a
    complete history, independent of whether WhatsApp/email are
    configured or reachable at the time.
    """

    LEVEL_CHOICES = [
        ("critical", "Critical"),
        ("important", "Important"),
        ("info", "Information"),
    ]

    branch = models.ForeignKey("tenants.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_path = models.CharField(
        max_length=200, blank=True,
        help_text="In-app route this notification is about, e.g. '/inventory' — lets the "
                   "frontend take the owner straight to the thing that needs attention.",
    )

    whatsapp_attempted = models.BooleanField(default=False)
    whatsapp_delivered = models.BooleanField(default=False)
    whatsapp_error = models.CharField(max_length=500, blank=True)

    email_attempted = models.BooleanField(default=False)
    email_delivered = models.BooleanField(default=False)
    email_error = models.CharField(max_length=500, blank=True)

    is_read = models.BooleanField(
        default=False,
        help_text="Whether anyone at the business has opened/acknowledged this yet — "
                   "drives the unread indicator in the app, separate from delivery status "
                   "above (a notification can be delivered by WhatsApp and still unread here).",
    )
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level}] {self.title}"
from django.db import models

from apps.core.crypto import EncryptedCharField


class PlatformSettings(models.Model):
    """Singleton row for deployment-wide integration credentials —
    the ones that belong to Truvanta itself, not to any one business:
    the WhatsApp Business number and Gmail account Truvanta sends
    notifications from, and Truvanta's own Paystack keys (for billing
    businesses that subscribe to the AI add-on). Editable by staff
    via the API so credentials can be added or rotated from the
    frontend without touching `.env` or redeploying.

    Falls back to `.env` values (see settings.py) when a field here
    is blank, so a fresh install still works from `.env` alone until
    someone sets these through the UI.
    """

    whatsapp_access_token = EncryptedCharField(max_length=500, blank=True, default="")
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True)

    email_host_user = models.CharField(max_length=255, blank=True)
    email_host_password = EncryptedCharField(
        max_length=255, blank=True, default="",
        help_text="A Gmail App Password, not the account password. Encrypted at rest.",
    )

    platform_paystack_public_key = models.CharField(max_length=200, blank=True)
    platform_paystack_secret_key = EncryptedCharField(max_length=200, blank=True, default="")

    rent_mode_enabled = models.BooleanField(
        default=False,
        help_text="Master switch for paid-feature enforcement. OFF: every feature is unlocked for "
                   "every business, regardless of subscription — billing exists but isn't enforced. "
                   "ON: gated features (see billing.Feature) require an active Plan or an admin "
                   "override. Meant to be flipped freely — e.g. off during a demo or free period, "
                   "on when you're ready to start charging — with no other changes needed.",
    )

    # --- Admin console quick-access PIN ---    # Deliberately has NO default value — the first platform staff
    # member to open the admin panel sets it themselves (see
    # AdminPinUnlockView). This is a convenience unlock for staff who
    # are already fully authenticated with a real account (is_staff
    # required to even reach it) — not a replacement for real login.
    admin_pin_hash = models.CharField(max_length=255, blank=True, default="")
    admin_pin_set_at = models.DateTimeField(null=True, blank=True)
    admin_pin_failed_attempts = models.PositiveIntegerField(default=0)
    admin_pin_locked_until = models.DateTimeField(null=True, blank=True)

    universal_color = models.CharField(
        max_length=7, default="#E3A635",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a hex color like #E3A635.")],
        help_text="The platform's default accent color — shown on the login screen and used by "
                   "any business that hasn't picked its own branding color yet. A business's own "
                   "color (Settings → Business branding) always takes priority over this once set.",
    )

    minimum_client_version = models.CharField(
        max_length=20, blank=True, default="",
        help_text="If set, any frontend build older than this version is blocked behind a "
                   "full-screen 'please refresh' notice — for forcing everyone onto a build with "
                   "a critical fix (e.g. ledger math) before they can keep working. Leave blank to "
                   "never force a refresh. Format: e.g. '1.2.0'.",
    )

    google_oauth_client_id = models.CharField(
        max_length=255, blank=True, default="",
        help_text="From Google Cloud Console (APIs & Services > Credentials > OAuth 2.0 Client "
                   "ID, type 'Web application'). Not a secret — this is meant to be visible in "
                   "frontend JS, unlike the values above. Leave blank to keep 'Sign in with "
                   "Google' hidden on the login screen.",
    )

    trial_grace_days = models.IntegerField(
        default=0,
        help_text="After a trial or subscription lapses, how many days to keep a reduced set of "
                   "features working (see trial_grace_feature_count and Feature.lock_priority) "
                   "before locking everything down to just the free core. 0 means lock "
                   "everything immediately, the same as before this setting existed.",
    )
    trial_grace_feature_count = models.IntegerField(
        default=0,
        help_text="During the grace window above, how many features (ranked by lowest "
                   "lock_priority first) stay usable. E.g. 2 keeps only the two features an "
                   "admin has marked as least urgent to lock working; everything else locks "
                   "right away. Ignored when trial_grace_days is 0.",
    )

    feature_hub_overrides = models.JSONField(
        default=dict, blank=True,
        help_text="Platform-admin overrides for which dashboard (Sell & Buy / Security / "
                   "Business Health) a feature currently lives under, keyed by feature key. "
                   "A feature not present here uses its built-in default hub. Applies to "
                   "every business — this is a layout decision, not a per-business setting.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"

    def __str__(self):
        return "Platform Settings"

    @classmethod
    def load(cls) -> "PlatformSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
