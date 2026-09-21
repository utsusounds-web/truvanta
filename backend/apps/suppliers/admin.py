from django.contrib import admin
from .models import Supplier, SupplierLedgerEntry, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem

admin.site.register(Supplier)
admin.site.register(SupplierLedgerEntry)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(GoodsReceipt)
admin.site.register(GoodsReceiptItem)
