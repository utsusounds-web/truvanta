from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class Quotation(TenantScopedModel):
    """A price quote or proforma invoice given to a customer before
    money changes hands (spec section 7). The two are the same
    document shape — line items, a total, a validity window — with a
    different purpose: a quotation is 'here's what this would cost',
    a proforma invoice is 'send payment against this before we
    proceed' (common for deposits, imports, or B2B customers whose
    own accounts department requires one before releasing funds).

    Deliberately NOT a Sale: nothing here touches inventory or the
    ledger until it's actually accepted and converted (see
    services.convert_to_sale) — a quote that's never accepted must
    leave zero trace on stock or financials, and a business should be
    able to issue as many draft quotes as it likes without them
    counting as anything real yet.
    """
    DOCUMENT_TYPE_CHOICES = [
        ("quotation", "Quotation"),
        ("proforma_invoice", "Proforma Invoice"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("converted", "Converted to Sale"),
        ("void", "Void"),
    ]

    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default="quotation")
    reference_number = models.CharField(max_length=50)
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="quotations")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    valid_until = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    # Set only once converted — the resulting Sale is the single
    # source of truth for financials/inventory from that point on;
    # this is just a pointer back to it.
    converted_sale = models.ForeignKey(
        "sales.Sale", on_delete=models.SET_NULL, null=True, blank=True, related_name="originating_quotation",
    )

    class Meta:
        unique_together = [("business", "reference_number")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} {self.reference_number}"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))


class QuotationItem(TenantScopedModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    unit = models.ForeignKey("products.UnitOfMeasure", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    @property
    def line_total(self):
        return (self.quantity * self.unit_price) - self.discount_amount
