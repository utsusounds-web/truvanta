from rest_framework.routers import DefaultRouter

from .views import QuotationViewSet, QuotationItemViewSet

router = DefaultRouter()
router.register("quotations", QuotationViewSet, basename="quotation")
router.register("quotation-items", QuotationItemViewSet, basename="quotation-item")

urlpatterns = router.urls
