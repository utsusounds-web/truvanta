from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet, SupplierLedgerEntryViewSet, PurchaseOrderViewSet,
    PurchaseOrderItemViewSet, GoodsReceiptViewSet,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("supplier-ledger-entries", SupplierLedgerEntryViewSet, basename="supplier-ledger-entry")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("purchase-order-items", PurchaseOrderItemViewSet, basename="purchase-order-item")
router.register("goods-receipts", GoodsReceiptViewSet, basename="goods-receipt")
urlpatterns = router.urls
