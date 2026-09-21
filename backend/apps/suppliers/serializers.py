from rest_framework import serializers
from .models import Supplier, SupplierLedgerEntry, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem


class SupplierSerializer(serializers.ModelSerializer):
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Supplier
        fields = ["id", "name", "phone_number", "email", "address", "is_active", "outstanding_balance"]
        read_only_fields = ["id"]


class SupplierLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierLedgerEntry
        fields = ["id", "supplier", "entry_type", "amount", "reference_note", "created_at"]
        read_only_fields = ["id", "created_at"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "purchase_order", "product", "unit", "quantity_ordered", "unit_cost"]
        read_only_fields = ["id"]

    def validate_product(self, product):
        # A supplier delivers physical goods — never a "bundle", which
        # is an in-app sales concept with no stock of its own (see
        # Product.is_bundle). Ordering one here would create a real
        # StockLevel for something sales never draws down from.
        if product.is_bundle:
            raise serializers.ValidationError("A bundle can't be purchased directly — order its component products instead.")
        return product


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "supplier", "branch", "reference_number", "status", "created_by", "notes", "expected_delivery_date", "items"]
        read_only_fields = ["id", "created_by"]


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptItem
        fields = ["id", "goods_receipt", "purchase_order_item", "quantity_received", "quantity_damaged", "quantity_missing"]
        read_only_fields = ["id"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = ["id", "purchase_order", "received_by", "notes", "items"]
        read_only_fields = ["id", "received_by"]
