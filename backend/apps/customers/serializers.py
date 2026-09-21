from rest_framework import serializers
from .models import Customer, CustomerCreditTransaction


class CustomerSerializer(serializers.ModelSerializer):
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "phone_number", "email", "photo", "address", "credit_limit", "is_active", "outstanding_balance"]
        read_only_fields = ["id"]


class CustomerCreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerCreditTransaction
        fields = ["id", "customer", "entry_type", "amount", "due_date", "reference_note", "created_at", "client_reference"]
        read_only_fields = ["id", "created_at"]
