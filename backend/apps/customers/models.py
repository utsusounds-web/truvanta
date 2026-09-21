from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class Customer(TenantScopedModel):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to="customer_photos/", null=True, blank=True)
    address = models.CharField(max_length=500, blank=True)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["business", "phone_number"])]

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        agg = self.credit_transactions.aggregate(total=models.Sum("amount"))
        return agg["total"] or 0


class CustomerCreditTransaction(TenantScopedModel):
    """Ledger entry for a customer's account. A credit sale posts a
    positive (debt-increasing) entry; a payment posts a negative
    (debt-reducing) entry. Balance is always the sum of this ledger —
    never a manually edited field — so it can't silently drift.
    """
    ENTRY_TYPE_CHOICES = [
        ("credit_sale", "Credit Sale"),
        ("payment", "Payment Received"),
        ("adjustment", "Adjustment"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="credit_transactions")
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Positive increases debt, negative reduces it.")
    due_date = models.DateField(null=True, blank=True)
    reference_note = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=64, blank=True)
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    client_reference = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Client-generated idempotency key for payments recorded while offline.",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client_reference"],
                condition=models.Q(client_reference__isnull=False),
                name="unique_credit_txn_client_reference_per_business",
            )
        ]

    def __str__(self):
        return f"{self.customer.name} {self.entry_type} {self.amount}"
