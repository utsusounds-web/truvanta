from rest_framework import serializers

from .models import Category, Brand, UnitOfMeasure, Product, ProductUnit, ProductBatch, ProductBundleItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent"]
        read_only_fields = ["id"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]
        read_only_fields = ["id"]


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ["id", "name", "abbreviation"]
        read_only_fields = ["id"]


class ProductUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUnit
        fields = ["id", "product", "unit", "conversion_factor_to_base", "is_default_sales_unit", "is_default_purchase_unit"]
        read_only_fields = ["id", "product"]


class ProductBundleItemSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source="component.name", read_only=True)

    class Meta:
        model = ProductBundleItem
        fields = ["id", "bundle", "component", "component_name", "quantity"]
        read_only_fields = ["id", "bundle"]


class VariantSummarySerializer(serializers.ModelSerializer):
    """Lightweight view of a variant for nesting under its parent —
    the full ProductSerializer would be redundant/circular here."""
    class Meta:
        model = Product
        fields = ["id", "name", "sku", "barcode", "variant_attributes", "cost_price", "selling_price", "is_active"]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    units = ProductUnitSerializer(many=True, read_only=True)
    variants = VariantSummarySerializer(many=True, read_only=True)
    bundle_items = ProductBundleItemSerializer(many=True, read_only=True)
    parent_product_name = serializers.CharField(source="parent_product.name", read_only=True, default=None)
    profit_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    profit_margin_percent = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    is_at_loss = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "barcode", "category", "brand", "image", "base_unit",
            "cost_price", "selling_price", "minimum_stock_level", "reorder_level",
            "track_batches", "track_expiry", "is_active", "units",
            "parent_product", "parent_product_name", "variant_attributes", "variants",
            "is_bundle", "bundle_items",
            "profit_amount", "profit_margin_percent", "is_at_loss",
        ]
        read_only_fields = ["id"]

    # SECURITY: this must live here, not just in what the frontend
    # chooses to render. A permission enforced only by hiding a
    # column is not a permission — anyone with a valid session token
    # can call this endpoint directly and read every field it
    # returns, frontend or not. cost_price and everything derived
    # from it are profit-sensitive (see Products view history: this
    # was previously "fixed" only by hiding table columns client-side,
    # which fixed nothing at the API level).
    PROFIT_FIELDS = ("cost_price", "profit_amount", "profit_margin_percent", "is_at_loss")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        membership = getattr(request, "membership", None) if request else None
        can_view_profit = bool(membership and membership.has_permission("view_profit"))
        if not can_view_profit:
            for field in self.PROFIT_FIELDS:
                data.pop(field, None)
            for v in data.get("variants") or []:
                v.pop("cost_price", None)
        return data

    def validate(self, data):
        parent = data.get("parent_product", getattr(self.instance, "parent_product", None))
        is_bundle = data.get("is_bundle", getattr(self.instance, "is_bundle", False))
        if parent and is_bundle:
            raise serializers.ValidationError("A variant can't also be a bundle.")
        if parent and parent.parent_product_id:
            raise serializers.ValidationError("A variant can't itself have variants — link to the top-level product instead.")
        if parent and parent.is_bundle:
            raise serializers.ValidationError("A bundle can't have variants.")
        if self.instance and parent and self.instance.id == parent.id:
            raise serializers.ValidationError("A product can't be its own variant parent.")
        return data


class ProductBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBatch
        fields = ["id", "product", "branch", "batch_number", "expiry_date", "quantity_received"]
        read_only_fields = ["id"]
