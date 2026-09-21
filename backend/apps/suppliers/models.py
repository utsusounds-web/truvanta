from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class Supplier(TenantScopedModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        agg = self.ledger_entries.aggregate(total=models.Sum("amount"))
        return agg["total"] or 0


class SupplierLedgerEntry(TenantScopedModel):
    ENTRY_TYPE_CHOICES = [
        ("purchase", "Purchase (Invoice)"),
        ("payment", "Payment Made"),
        ("adjustment", "Adjustment"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="ledger_entries")
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Positive increases what we owe, negative reduces it.")
    reference_note = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=64, blank=True)
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class PurchaseOrder(TenantScopedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent to Supplier"),
        ("partially_received", "Partially Received"),
        ("received", "Fully Received"),
        ("cancelled", "Cancelled"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="purchase_orders")
    reference_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    expected_delivery_date = models.DateField(
        null=True, blank=True,
        help_text="What the supplier promised, if given — powers the on-time % in the Supplier Reliability "
                   "Scorecard. Left blank, this PO simply isn't counted in that metric rather than guessed at.",
    )

    class Meta:
        unique_together = [("business", "reference_number")]

    def __str__(self):
        return self.reference_number


class PurchaseOrderItem(TenantScopedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    unit = models.ForeignKey("products.UnitOfMeasure", on_delete=models.PROTECT)
    quantity_ordered = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2)


class GoodsReceipt(TenantScopedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts")
    received_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)


class GoodsReceiptItem(TenantScopedModel):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="items")
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_damaged = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    quantity_missing = models.DecimalField(max_digits=14, decimal_places=3, default=0)
