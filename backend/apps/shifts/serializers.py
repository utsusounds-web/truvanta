from rest_framework import serializers

from .models import Shift


class ShiftOpenSerializer(serializers.Serializer):
    branch = serializers.UUIDField()
    opening_cash = serializers.DecimalField(max_digits=14, decimal_places=2)


class ShiftCloseSerializer(serializers.Serializer):
    closing_physical_cash = serializers.DecimalField(max_digits=14, decimal_places=2)


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id", "branch", "employee", "opening_cash", "opened_at",
            "closing_physical_cash", "expected_closing_cash", "variance", "closed_at",
            "status", "result", "reviewed_by", "reviewed_at", "review_note",
        ]
        read_only_fields = fields
