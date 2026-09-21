from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class SaleReturn(TenantScopedModel):
    """A customer return/refund/exchange against a completed Sale.
    Kept as its own record (never a destructive edit to the Sale) so
    the original transaction and the correction are both visible in
    history — see apps.returns.services for the inventory/cash/audit
    side effects this triggers.
    """

    TYPE_CHOICES = [
        ("return", "Return (restock)"),
        ("refund", "Refund"),
        ("exchange", "Exchange"),
        ("damaged", "Damaged Goods"),
        ("expired", "Expired Product"),
    ]
    STATUS_CHOICES = [
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    sale = models.ForeignKey("sales.Sale", on_delete=models.PROTECT, related_name="returns")
    sale_item = models.ForeignKey("sales.SaleItem", on_delete=models.PROTECT, related_name="returns")
    return_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    restock = models.BooleanField(default=True, help_text="Whether returned quantity goes back into sellable stock.")
    reason = models.CharField(max_length=500)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending_approval")
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="requested_returns",
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_returns",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.return_type} for {self.sale.transaction_number}"


class SupplierReturn(TenantScopedModel):
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="returns")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.CharField(max_length=500)
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
