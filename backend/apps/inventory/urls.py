from rest_framework.routers import DefaultRouter

from .views import StockLevelViewSet, StockMovementViewSet, StockTransferViewSet

router = DefaultRouter()
router.register("stock-levels", StockLevelViewSet, basename="stock-level")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("stock-transfers", StockTransferViewSet, basename="stock-transfer")

urlpatterns = router.urls
