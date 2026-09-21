import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class ExchangeRate(models.Model):
    """A manually-entered conversion rate to the business's own
    currency (Business.currency_code) — there's no live forex feed
    here, so this is only as current as whoever last updated it. Set
    by the owner/admin once (e.g. each morning); the POS uses the
    latest rate for a currency as the default when a cashier records a
    payment made in that currency, but the cashier can always override
    it per-payment if the street rate differs (see Payment below).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="exchange_rates")
    currency_code = models.CharField(max_length=8, help_text="The foreign currency, e.g. 'USD'.")
    rate_to_business_currency = models.DecimalField(
        max_digits=14, decimal_places=6,
        validators=[MinValueValidator(0.000001)],
        help_text="1 unit of currency_code = this many units of the business's own currency.",
    )
    set_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["business", "currency_code", "-created_at"])]

    def __str__(self):
        return f"1 {self.currency_code} = {self.rate_to_business_currency} ({self.business.currency_code})"


class Sale(TenantScopedModel):
    """A completed (or controlled-cancelled) transaction. Completed
    sales are never deleted — see `cancel()`/refund flow in
    apps.sales.services, which posts reversing StockMovements and a
    new Return/Refund record instead of touching this row's totals.
    """

    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("partially_refunded", "Partially Refunded"),
        ("refunded", "Fully Refunded"),
    ]
    SALE_TYPE_CHOICES = [
        ("cash", "Cash / Immediate Payment"),
        ("credit", "Credit Sale"),
    ]

    transaction_number = models.CharField(max_length=40, unique=True, editable=False)
    client_reference = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Client-generated idempotency key. Set when a sale is created from an offline "
                   "queue so a retried sync request can never post the same sale twice.",
    )
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="sales")
    cashier = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="sales")
    shift = models.ForeignKey("shifts.Shift", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales",
    )

    sale_type = models.CharField(max_length=10, choices=SALE_TYPE_CHOICES, default="cash")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "branch", "created_at"]),
            models.Index(fields=["business", "client_reference"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client_reference"],
                condition=models.Q(client_reference__isnull=False),
                name="unique_client_reference_per_business",
            )
        ]

    def __str__(self):
        return self.transaction_number

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = f"SL-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class SaleItem(TenantScopedModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sale_items")
    unit = models.ForeignKey("products.UnitOfMeasure", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class PaymentMethod(TenantScopedModel):
    """Owner-configurable payment methods (spec section 6). Four
    defaults are seeded per business the first time this is accessed
    (see services.ensure_default_payment_methods) — Cash, Bank
    Transfer, POS/Card, Other — matching what existed before this was
    configurable, so nothing already recorded ever points at a method
    that no longer exists. The owner can rename any of them, add more
    (Mobile Money, Cheque, Crypto, whatever fits the business), or
    deactivate ones they don't use — deactivating only hides a method
    from new sales, it never touches sales already recorded against
    it. 'cash' is protected: its code can't change and it can't be
    deactivated, because cash sales get special handling elsewhere
    (blind shift reconciliation, change-due calculation) that assumes
    a method with that exact code always exists.
    """
    code = models.SlugField(max_length=30, help_text="Stable identifier — 'cash' is reserved and can't be reused for a different method.")
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business", "code"], name="unique_payment_method_code_per_business"),
        ]

    def __str__(self):
        return f"{self.name} ({self.business_id})"


class Payment(TenantScopedModel):
    RECONCILIATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("reconciled", "Reconciled"),
        ("unmatched", "Unmatched"),
        ("disputed", "Disputed"),
    ]
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    # A plain code, not a FK — deliberately. A sale's payment record
    # must never change meaning just because a PaymentMethod row was
    # later renamed or deactivated; this stores what was actually
    # chosen at the time, validated against the business's active
    # methods at write time (see PaymentSerializer.validate_method).
    method = models.CharField(max_length=30)
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Always in the business's own currency (Business.currency_code) — "
                   "this is what every report/reconciliation/total reads from.",
    )
    reference = models.CharField(max_length=100, blank=True)

    # Optional — only set when the customer actually paid in a foreign
    # currency. `amount` above is still always computed in the business's
    # own currency (foreign_amount * exchange_rate_used, rounded), so
    # nothing downstream (reports, reconciliation, shift totals) needs
    # to know multi-currency exists at all.
    foreign_currency_code = models.CharField(max_length=8, blank=True)
    foreign_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    exchange_rate_used = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True,
        help_text="Rate actually used for this payment — captured at the time, even if the "
                   "reference ExchangeRate is edited or deleted later.",
    )

    reconciliation_status = models.CharField(
        max_length=20, choices=RECONCILIATION_STATUS_CHOICES, default="pending",
        help_text="Cash is self-evident at the till; bank transfer/card/other payments "
                   "start pending until matched against a bank or processor statement.",
    )
    reconciled_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciliation_note = models.CharField(max_length=500, blank=True)

    def save(self, *args, **kwargs):
        # Cash is verified in person at the point of sale — there's nothing
        # external to reconcile it against, so it doesn't sit in a pending
        # queue. Checked via existence rather than `self.pk` because these
        # models default their UUID pk at instantiation, not at save time —
        # `self.pk` is never falsy even for a brand-new, unsaved row.
        is_new = not Payment.objects.filter(pk=self.pk).exists()
        if is_new and self.method == "cash" and self.reconciliation_status == "pending":
            self.reconciliation_status = "confirmed"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.method}: {self.amount}"


class ReceiptPrintLog(TenantScopedModel):
    """Tracks every time a receipt is (re)printed, per section 8 of
    the spec — original prints are copy_number=1; any later print for
    the same sale is a reprint and must render 'REPRINT' on the
    document (enforced by the renderer using copy_number > 1)."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="print_logs")
    printed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    copy_number = models.PositiveIntegerField()

    class Meta:
        ordering = ["sale", "copy_number"]
