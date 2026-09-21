from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class Category(TenantScopedModel):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")

    class Meta:
        unique_together = [("business", "name", "parent")]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Brand(TenantScopedModel):
    name = models.CharField(max_length=150)

    class Meta:
        unique_together = [("business", "name")]

    def __str__(self):
        return self.name


class UnitOfMeasure(TenantScopedModel):
    """A sellable/stockable unit, e.g. Piece, Carton, Bottle, Kg."""
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10)

    class Meta:
        unique_together = [("business", "name")]

    def __str__(self):
        return self.abbreviation


class Product(TenantScopedModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    image = models.ImageField(upload_to="product_images/", null=True, blank=True)

    # Base unit is the smallest unit stock is tracked in internally (e.g. "Bottle").
    base_unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="base_products")

    cost_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])

    minimum_stock_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)

    track_batches = models.BooleanField(default=False)
    track_expiry = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    # --- Variants (spec section 5) ---
    # A variant is its own full Product row — it gets its own SKU,
    # barcode, price, and stock level for free, because every part of
    # the app (POS, inventory, sales, purchase orders, reports) already
    # operates on Product. parent_product links it back to the "family"
    # it belongs to, purely for grouping/display — selling a variant
    # behaves in every way like selling any other product. A product
    # with parent_product set is never itself the parent of another
    # variant (no nesting).
    parent_product = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="variants",
        help_text="Set this to make the product a variant of another product (e.g. this row is "
                   "'Red / Large' under the parent 'T-Shirt'). Leave blank for a standalone product.",
    )
    variant_attributes = models.JSONField(
        default=dict, blank=True,
        help_text="Free-form attributes distinguishing this variant, e.g. {\"color\": \"Red\", \"size\": \"Large\"}.",
    )

    # --- Bundles (spec section 5) ---
    # A bundle is also a Product row (sellable, has its own price), but
    # is never stocked directly — see ProductBundleItem below. Selling
    # a bundle deducts each *component's* stock instead of the
    # bundle's own (apps.sales.services.stock_deductions_for).
    is_bundle = models.BooleanField(default=False)

    class Meta:
        unique_together = [("business", "sku")]
        indexes = [models.Index(fields=["business", "barcode"])]

    def __str__(self):
        return self.name

    @property
    def profit_amount(self):
        return self.selling_price - self.cost_price

    @property
    def profit_margin_percent(self):
        if self.selling_price == 0:
            return 0
        return round((self.profit_amount / self.selling_price) * 100, 2)

    @property
    def is_at_loss(self):
        return self.selling_price < self.cost_price


class ProductBundleItem(TenantScopedModel):
    """One component of a bundle Product (Product.is_bundle=True).
    Selling `quantity` bundles deducts `quantity * quantity` of the
    component's own stock — the bundle itself is never separately
    stocked, so there's nothing to run out of except its components.
    """
    bundle = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bundle_items")
    component = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="used_in_bundles")
    quantity = models.DecimalField(
        max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)],
        help_text="How many of the component (in its base unit) one bundle sale consumes.",
    )

    class Meta:
        unique_together = [("bundle", "component")]

    def __str__(self):
        return f"{self.bundle.name}: {self.quantity} x {self.component.name}"


class ProductUnit(TenantScopedModel):
    """A conversion between the product's base unit and a purchasing/
    selling unit — e.g. 1 Carton = 24 Bottles. Receiving stock in
    'Carton' correctly increases stock by 24 in the base unit.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="units")
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT)
    conversion_factor_to_base = models.DecimalField(
        max_digits=14, decimal_places=4, validators=[MinValueValidator(0.0001)],
        help_text="How many base units 1 of this unit equals, e.g. 24 for Carton->Bottle.",
    )
    is_default_sales_unit = models.BooleanField(default=False)
    is_default_purchase_unit = models.BooleanField(default=False)

    class Meta:
        unique_together = [("product", "unit")]

    def __str__(self):
        return f"{self.product.name}: 1 {self.unit.abbreviation} = {self.conversion_factor_to_base} base units"


class ProductBatch(TenantScopedModel):
    """Optional batch/expiry tracking for a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    branch = models.ForeignKey("tenants.Branch", on_delete=models.CASCADE, related_name="product_batches")
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField(null=True, blank=True)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3)

    class Meta:
        unique_together = [("product", "branch", "batch_number")]

    def __str__(self):
        return f"{self.product.name} batch {self.batch_number}"


class PriceHistory(TenantScopedModel):
    """Records every change to a product's cost or selling price —
    what it replaced, what triggered it. This is what lets the system
    warn 'you're about to sell old stock at a loss' instead of just
    silently applying a new number.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    old_cost_price = models.DecimalField(max_digits=14, decimal_places=2)
    new_cost_price = models.DecimalField(max_digits=14, decimal_places=2)
    old_selling_price = models.DecimalField(max_digits=14, decimal_places=2)
    new_selling_price = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name}: cost {self.old_cost_price} -> {self.new_cost_price}"
