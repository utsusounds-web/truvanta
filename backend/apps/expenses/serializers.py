from rest_framework import serializers
from .models import ExpenseCategory, Expense, OwnerWithdrawal


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name"]
        read_only_fields = ["id"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id", "branch", "category", "amount", "reason", "receipt_image",
            "requested_by", "approved_by", "status", "created_at", "client_reference",
        ]
        read_only_fields = ["id", "requested_by", "approved_by", "created_at"]


class OwnerWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerWithdrawal
        fields = ["id", "branch", "amount", "note", "withdrawn_by", "created_at"]
        read_only_fields = ["id", "withdrawn_by", "created_at"]
