from django.db import models

from apps.core.models import TenantScopedModel


class QuickAudit(TenantScopedModel):
    """A random spot-check of physical stock against what the system
    expects (spec section 14). The owner triggers it; a random
    selection of products is generated (weighted toward higher-value
    and previously-discrepant items); the counting staff enters
    physical quantities; each line records the gap and its estimated
    financial impact for later review.
    """

    STATUS_CHOICES = [
        ("pending", "Pending — awaiting counts"),
        ("completed", "Completed"),
    ]

    branch = models.ForeignKey("tenants.Branch", on_delete=models.CASCADE, related_name="quick_audits")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    triggered_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="triggered_audits")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quick audit @ {self.branch.name} ({self.status})"


class QuickAuditLine(TenantScopedModel):
    audit = models.ForeignKey(QuickAudit, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="quick_audit_lines")
    expected_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    physical_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    counted_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    counted_at = models.DateTimeField(null=True, blank=True)

    @property
    def difference(self):
        if self.physical_quantity is None:
            return None
        return self.physical_quantity - self.expected_quantity

    @property
    def estimated_financial_value(self):
        if self.physical_quantity is None:
            return None
        return self.difference * self.product.cost_price

    def __str__(self):
        return f"{self.product.name}: expected {self.expected_quantity}"
