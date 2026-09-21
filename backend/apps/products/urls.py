from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet, BrandViewSet, UnitOfMeasureViewSet,
    ProductViewSet, ProductUnitViewSet, ProductBatchViewSet, ProductBundleItemViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("units", UnitOfMeasureViewSet, basename="unit")
router.register("products", ProductViewSet, basename="product")
router.register("product-units", ProductUnitViewSet, basename="product-unit")
router.register("product-batches", ProductBatchViewSet, basename="product-batch")
router.register("product-bundle-items", ProductBundleItemViewSet, basename="product-bundle-item")

urlpatterns = router.urls
