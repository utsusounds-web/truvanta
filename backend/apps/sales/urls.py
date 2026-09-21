from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    SaleViewSet, SaleVerifyView, ReceiptPrintLogViewSet, PaymentReconciliationViewSet, ExchangeRateViewSet,
    PaymentMethodViewSet,
)

router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("receipt-print-logs", ReceiptPrintLogViewSet, basename="receipt-print-log")
router.register("payment-reconciliation", PaymentReconciliationViewSet, basename="payment-reconciliation")
router.register("exchange-rates", ExchangeRateViewSet, basename="exchange-rate")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")

urlpatterns = router.urls + [
    path("verify/<uuid:sale_id>/", SaleVerifyView.as_view(), name="sale-verify"),
]
