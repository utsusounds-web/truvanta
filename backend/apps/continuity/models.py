from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class ContinuitySettings(TenantScopedModel):
    """One row per business (off by default — this is an opt-in
    safety net, not a default behavior). The owner names a backup
    manager and a threshold; if every owner-role member of the
    business has been inactive past that threshold, the backup
    manager's access is temporarily elevated to owner-level so the
    business isn't stuck — approvals, staff issues, an urgent expense
    — with nobody who can act.
    """
    is_enabled = models.BooleanField(default=False)
    backup_manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="continuity_backup_for",
        help_text="Must already have a Membership on this business — this doesn't invite a new person, "
                   "it elevates an existing staff member's access temporarily.",
    )
    inactivity_threshold_days = models.PositiveSmallIntegerField(
        default=14, validators=[MinValueValidator(3)],
        help_text="If every owner has been inactive this many days, continuity mode activates.",
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business"], name="one_continuity_settings_per_business")]

    def __str__(self):
        return f"Continuity settings for {self.business_id}"


class ContinuityActivation(TenantScopedModel):
    """One row per time continuity mode actually turned on — the
    audit trail for a mechanism that grants elevated access
    automatically has to be at least as rigorous as one granted by a
    human, arguably more so since nobody consciously approved this
    specific instance of it. Never deleted; deactivated_at is set,
    the row stays.
    """
    backup_manager = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="continuity_activations")
    activated_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-activated_at"]

    @property
    def is_active(self):
        return self.deactivated_at is None
