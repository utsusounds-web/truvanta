from django.core.validators import MinValueValidator
from django.db import models, transaction

from apps.core.models import TenantScopedModel


class StockLevel(TenantScopedModel):
    """Cached current stock, in the product's base unit, per branch.

    This is a derived/cached value — the source of truth is the
    StockMovement history. It exists purely so reads (POS product
    search, low-stock reports) don't need to sum movements every time.
    It must only ever be changed by StockMovement.save(), never
    directly, so it can never drift from the movement history.
    """
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_levels")
    branch = models.ForeignKey("tenants.Branch", on_delete=models.CASCADE, related_name="stock_levels")
    quantity = models.DecimalField(max_digits=16, decimal_places=3, default=0)

    class Meta:
        unique_together = [("product", "branch")]

    def __str__(self):
        return f"{self.product.name} @ {self.branch.name}: {self.quantity}"


class StockTransfer(TenantScopedModel):
    """A stock movement between two branches of the same business.
    Deducting from the sending branch and confirming receipt are two
    separate steps (spec section 19): the receiving branch confirms
    what actually arrived, and any gap between sent and received is
    recorded as a visible discrepancy rather than silently absorbed.
    """

    STATUS_CHOICES = [
        ("pending", "Pending — awaiting receipt"),
        ("received", "Received — matches sent"),
        ("received_with_discrepancy", "Received — quantity differs"),
    ]

    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="transfers")
    from_branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="transfers_sent")
    to_branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="transfers_received")
    quantity_sent = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    note = models.CharField(max_length=255, blank=True)
    sent_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_sent")
    received_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="transfers_received_by")
    sent_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.product.name}: {self.from_branch.name} -> {self.to_branch.name} ({self.status})"


class StockMovement(TenantScopedModel):
    """The single source of truth for inventory. Every change in stock
    — a sale, a purchase, a return, a transfer, an adjustment — must
    be recorded here. Nothing is allowed to directly overwrite
    StockLevel.quantity; it is always derived by applying movements.
    """

    REASON_CHOICES = [
        ("opening_stock", "Opening Stock"),
        ("purchase", "Stock Purchase"),
        ("sale", "Sale"),
        ("customer_return", "Customer Return"),
        ("supplier_return", "Supplier Return"),
        ("damage", "Damage"),
        ("expiry", "Expiry"),
        ("adjustment", "Stock Adjustment"),
        ("branch_transfer_out", "Branch Transfer Out"),
        ("branch_transfer_in", "Branch Transfer In"),
        ("promotional_sample", "Promotional Sample"),
        ("personal_use", "Personal Use"),
        ("other", "Other Authorized Movement"),
    ]

    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="stock_movements")
    branch = models.ForeignKey("tenants.Branch", on_delete=models.PROTECT, related_name="stock_movements")

    # Positive = stock increase, negative = stock decrease, expressed in the product's base unit.
    quantity_delta = models.DecimalField(max_digits=16, decimal_places=3)

    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reference_note = models.CharField(max_length=255, blank=True)

    client_reference = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Client-generated idempotency key for movements queued while offline, so a retried "
                   "sync request can never post the same adjustment twice.",
    )

    # Generic-ish links to the source document without hard FK coupling to every app.
    source_type = models.CharField(max_length=50, blank=True)  # e.g. "sale", "purchase_order"
    source_id = models.CharField(max_length=64, blank=True)

    performed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "product", "branch"]),
            models.Index(fields=["source_type", "source_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client_reference"],
                condition=models.Q(client_reference__isnull=False),
                name="unique_movement_client_reference_per_business",
            )
        ]

    def __str__(self):
        return f"{self.product.name} {self.quantity_delta:+} ({self.reason})"

    def save(self, *args, **kwargs):
        """Movements are append-only; disallow edits after creation so
        the audit history can never be silently rewritten."""
        if self.pk and StockMovement.objects.filter(pk=self.pk).exists():
            raise ValueError("StockMovement entries are immutable. Record a reversing movement instead.")
        is_new = self.pk is None or not StockMovement.objects.filter(pk=self.pk).exists()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                level, _ = StockLevel.objects.select_for_update().get_or_create(
                    business=self.business, product=self.product, branch=self.branch,
                    defaults={"quantity": 0},
                )
                was_negative_already = level.quantity < 0
                level.quantity = level.quantity + self.quantity_delta
                level.save(update_fields=["quantity", "updated_at"])
                # Never block the operation over this — refusing a sale
                # because the stock count looks wrong costs real revenue
                # and is usually the wrong call. Instead, surface it: a
                # negative on-hand quantity almost always means either a
                # missed purchase/opening-stock entry or genuine
                # shrinkage, and the owner should be the one to decide
                # which, not have it silently absorbed into the number.
                if level.quantity < 0 and not was_negative_already:
                    from apps.notifications.services import notify
                    notify(
                        business=self.business, branch=self.branch, level="critical",
                        title=f"Stock went negative: {self.product.name}",
                        message=f"{self.product.name} at {self.branch.name} is now showing {level.quantity} "
                                f"in stock. This usually means a purchase or opening-stock entry is missing, "
                                f"or stock is missing. Worth checking with a Quick Stock Audit.",
                        link_path="/quick-audit",
                    )

    def delete(self, *args, **kwargs):
        raise ValueError("StockMovement entries cannot be deleted. Record a reversing movement instead.")
