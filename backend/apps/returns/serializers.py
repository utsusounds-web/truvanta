from rest_framework import serializers
from .models import SaleReturn, SupplierReturn


class SaleReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleReturn
        fields = [
            "id", "sale", "sale_item", "return_type", "quantity", "refund_amount",
            "restock", "reason", "status", "requested_by", "approved_by", "created_at",
        ]
        read_only_fields = ["id", "requested_by", "approved_by", "status", "created_at"]


class SupplierReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierReturn
        fields = ["id", "supplier", "product", "branch", "quantity", "reason", "requested_by"]
        read_only_fields = ["id", "requested_by"]
