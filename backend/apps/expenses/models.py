from django.db import models

from apps.core.models import TenantScopedModel


class ExpenseCategory(TenantScopedModel):
    name = models.CharField(max_length=150)

    class Meta:
        unique_together = [("business", "name")]
        verbose_name_plural = "expense categories"

    def __str__(self):
        return self.name


class Expense(TenantScopedModel):
    """A business expense. Deliberately separate from owner
    withdrawals (see OwnerWithdrawal) so personal and business money
    are never mixed in reporting."""

    STATUS_CHOICES = [
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("voided", "Voided"),
    ]
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="expenses")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=500)
    receipt_image = models.ImageField(upload_to="expense_receipts/", null=True, blank=True)
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_expenses",
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_expenses",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_approval")
    client_reference = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Client-generated idempotency key for expenses recorded while offline.",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client_reference"],
                condition=models.Q(client_reference__isnull=False),
                name="unique_expense_client_reference_per_business",
            )
        ]

    def __str__(self):
        return f"{self.category.name}: {self.amount}"


class OwnerWithdrawal(TenantScopedModel):
    """Owner taking cash out for personal use — tracked separately
    from business Expense so financial reports never conflate the
    two."""
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="owner_withdrawals")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    withdrawn_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
