from rest_framework import serializers

from apps.sales.serializers import PaymentInputSerializer
from .models import Quotation, QuotationItem


class QuotationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = QuotationItem
        fields = ["id", "quotation", "product", "product_name", "unit", "quantity", "unit_price", "discount_amount", "line_total"]
        read_only_fields = ["id", "quotation"]


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id", "document_type", "reference_number", "branch", "customer", "customer_name",
            "status", "valid_until", "notes", "created_by", "converted_sale", "items", "subtotal", "created_at",
        ]
        read_only_fields = ["id", "reference_number", "status", "created_by", "converted_sale", "created_at"]


class ConvertToSaleSerializer(serializers.Serializer):
    sale_type = serializers.ChoiceField(choices=["cash", "credit"], default="cash")
    shift = serializers.CharField(required=False, allow_null=True)
    payments = PaymentInputSerializer(many=True, required=False)

    def validate(self, data):
        if data.get("sale_type") == "cash" and not data.get("payments"):
            raise serializers.ValidationError("Cash sales need at least one payment.")
        return data
