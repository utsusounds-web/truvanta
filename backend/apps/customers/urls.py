from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerCreditTransactionViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("customer-credit-transactions", CustomerCreditTransactionViewSet, basename="customer-credit-transaction")
urlpatterns = router.urls
