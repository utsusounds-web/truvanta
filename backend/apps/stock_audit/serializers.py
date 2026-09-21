from rest_framework import serializers
from .models import QuickAudit, QuickAuditLine


class QuickAuditLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    difference = serializers.SerializerMethodField()
    estimated_financial_value = serializers.SerializerMethodField()

    class Meta:
        model = QuickAuditLine
        fields = [
            "id", "product", "product_name", "expected_quantity", "physical_quantity",
            "difference", "estimated_financial_value", "counted_by", "counted_at",
        ]
        read_only_fields = ["id", "product", "expected_quantity", "counted_by", "counted_at"]

    def get_difference(self, obj):
        d = obj.difference
        return str(d) if d is not None else None

    def get_estimated_financial_value(self, obj):
        v = obj.estimated_financial_value
        return str(v) if v is not None else None


class QuickAuditSerializer(serializers.ModelSerializer):
    lines = QuickAuditLineSerializer(many=True, read_only=True)

    class Meta:
        model = QuickAudit
        fields = ["id", "branch", "status", "triggered_by", "completed_at", "created_at", "lines"]
        read_only_fields = fields
