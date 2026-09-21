from rest_framework.routers import DefaultRouter
from .views import SaleReturnViewSet, SupplierReturnViewSet

router = DefaultRouter()
router.register("sale-returns", SaleReturnViewSet, basename="sale-return")
router.register("supplier-returns", SupplierReturnViewSet, basename="supplier-return")
urlpatterns = router.urls
