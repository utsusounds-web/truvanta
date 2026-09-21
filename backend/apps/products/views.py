from decimal import Decimal, InvalidOperation

from django.utils.text import slugify
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from apps.core.viewsets import TenantScopedModelViewSet
from apps.core.permissions import IsBusinessMember, HasBusinessPermission
from .models import Category, Brand, UnitOfMeasure, Product, ProductUnit, ProductBatch, ProductBundleItem
from .serializers import (
    CategorySerializer, BrandSerializer, UnitOfMeasureSerializer,
    ProductSerializer, ProductUnitSerializer, ProductBatchSerializer, ProductBundleItemSerializer,
)
from . import services


class RequireManageProducts(HasBusinessPermission):
    required_permission_code = "manage_products"


def _unique_sku(business_id, name: str) -> str:
    """Collision-safe fallback when the owner doesn't set a SKU: base
    it on the product name, then append a counter if that's taken —
    never just silently truncate and hope, which is how two products
    both named 'Rice ...' used to collide.
    """
    base = (slugify(name) or "item")[:16].upper().replace("-", "")
    sku = base
    n = 1
    while Product.objects.filter(business_id=business_id, sku=sku).exists():
        n += 1
        suffix = str(n)
        sku = f"{base[: 16 - len(suffix) - 1]}-{suffix}"
    return sku


class CategoryViewSet(TenantScopedModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BrandViewSet(TenantScopedModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


class UnitOfMeasureViewSet(TenantScopedModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer

    def get_queryset(self):
        from . import services
        from apps.tenants.models import Business
        services.ensure_default_units(Business.objects.get(pk=self.request.business_id))
        return super().get_queryset()


class ProductViewSet(TenantScopedModelViewSet):
    queryset = Product.objects.select_related("category", "brand", "base_unit", "parent_product").prefetch_related("units", "variants", "bundle_items__component")
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["is_active", "category", "brand", "parent_product", "is_bundle"]
    search_fields = ["name", "sku", "barcode"]

    def get_permissions(self):
        # Everyone in the business needs to read the product catalog
        # (POS, Inventory, Purchase Orders, Transfers all depend on
        # it). Creating, editing, or deleting products — including
        # changing prices — is "manage_products" territory.
        if self.action in ("list", "retrieve", "suggest_price"):
            return [IsBusinessMember()]
        return [RequireManageProducts()]

    def perform_create(self, serializer):
        sku = serializer.validated_data.get("sku") or ""
        extra = {}
        if not sku.strip():
            extra["sku"] = _unique_sku(self.request.business_id, serializer.validated_data.get("name", ""))
        # DRF treats a BooleanField missing from multipart/form data as
        # an unchecked HTML checkbox (False), not "use the model
        # default". The Add-product forms submit multipart (for image
        # upload) and never send is_active — so every product created
        # there was silently saved permanently inactive, invisible to
        # every screen that correctly filters on is_active=true (POS,
        # Inventory, Purchase Orders, Transfers, Quick Audit). Force
        # the real default whenever the caller didn't explicitly send one.
        if "is_active" not in self.request.data:
            extra["is_active"] = True
        serializer.save(business_id=self.request.business_id, **extra)

    @action(detail=True, methods=["get"], url_path="suggest-price")
    def suggest_price(self, request, pk=None):
        """Preview what the selling price would need to be to keep
        the same margin, given a new cost price — without applying
        anything. Lets the UI show the suggestion before the owner commits."""
        product = self.get_object()
        try:
            new_cost = Decimal(str(request.query_params.get("new_cost_price", "")))
        except InvalidOperation:
            raise ValidationError({"new_cost_price": "Provide a valid number."})
        suggested = services.suggest_rebalanced_price(product, new_cost)
        current_stock = sum(
            float(l.quantity) for l in product.stock_levels.all()
        )
        would_be_at_loss_if_unchanged = product.selling_price < new_cost
        return Response({
            "current_cost_price": str(product.cost_price),
            "current_selling_price": str(product.selling_price),
            "new_cost_price": str(new_cost),
            "suggested_selling_price": str(suggested),
            "current_stock_on_hand": current_stock,
            "would_sell_at_loss_if_price_unchanged": would_be_at_loss_if_unchanged,
        })

    @action(detail=True, methods=["post"], url_path="update-cost-price")
    def update_cost_price(self, request, pk=None):
        """Apply a new cost price. Pass `new_selling_price` to also
        update the selling price (typically the suggested/confirmed
        value from suggest-price); otherwise only cost changes and
        the existing selling price is kept as-is."""
        product = self.get_object()
        try:
            new_cost = Decimal(str(request.data.get("new_cost_price", "")))
        except InvalidOperation:
            raise ValidationError({"new_cost_price": "Provide a valid number."})
        new_selling = request.data.get("new_selling_price")
        new_selling = Decimal(str(new_selling)) if new_selling not in (None, "") else None
        updated = services.update_cost_price(
            product=product, new_cost_price=new_cost, actor=request.user,
            new_selling_price=new_selling, reason=request.data.get("reason", ""),
        )
        return Response(ProductSerializer(updated).data)


class ProductUnitViewSet(TenantScopedModelViewSet):
    queryset = ProductUnit.objects.all()
    serializer_class = ProductUnitSerializer


class ProductBatchViewSet(TenantScopedModelViewSet):
    queryset = ProductBatch.objects.all()
    serializer_class = ProductBatchSerializer
    filterset_fields = ["product", "branch"]


class ProductBundleItemViewSet(TenantScopedModelViewSet):
    """Manages what's inside a bundle. Same permission split as
    Products itself — reading the recipe is fine for anyone who can
    see the catalog, changing it is a manage_products action since it
    changes what actually gets deducted from stock on every sale."""
    queryset = ProductBundleItem.objects.select_related("bundle", "component").all()
    serializer_class = ProductBundleItemSerializer
    filterset_fields = ["bundle"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsBusinessMember()]
        return [RequireManageProducts()]

    def perform_create(self, serializer):
        bundle = serializer.validated_data["bundle"]
        component = serializer.validated_data["component"]
        if not bundle.is_bundle:
            raise ValidationError("That product isn't marked as a bundle.")
        if component.is_bundle:
            raise ValidationError("A bundle can't contain another bundle.")
        if bundle.id == component.id:
            raise ValidationError("A bundle can't contain itself.")
        serializer.save(business_id=self.request.business_id)
