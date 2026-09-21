from django.db import models

from apps.core.models import TenantScopedModel


class Shift(TenantScopedModel):
    """An employee's cash-handling session. Closing is a *blind*
    count: the employee enters the physical cash counted before the
    system reveals the expected amount (enforced at the API/service
    layer, not here) — this is what makes the reconciliation
    meaningful rather than a rubber stamp.
    """

    STATUS_CHOICES = [
        ("open", "Open"),
        ("pending_review", "Pending Review"),
        ("reviewed", "Reviewed"),
    ]
    RESULT_CHOICES = [
        ("balanced", "Balanced"),
        ("over", "Cash Over"),
        ("short", "Cash Short"),
        ("requires_review", "Requires Review"),
    ]

    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="shifts")
    employee = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="shifts")

    opening_cash = models.DecimalField(max_digits=14, decimal_places=2)
    opened_at = models.DateTimeField(auto_now_add=True)

    closing_physical_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expected_closing_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)

    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_shifts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Shift {self.employee.email} @ {self.branch.name} ({self.status})"
