from rest_framework import serializers

from .models import Sale, SaleItem, Payment, ReceiptPrintLog, ExchangeRate, PaymentMethod


class SaleItemInputSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    unit = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)


class PaymentInputSerializer(serializers.Serializer):
    # Not a ChoiceField: which codes are valid depends on the
    # business's own configured PaymentMethod list, checked in
    # SaleViewSet.create where the business is known. This keeps the
    # serializer itself business-agnostic while still rejecting a
    # bogus/inactive method before a sale is ever posted.
    method = serializers.CharField(max_length=30)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False,
        help_text="Required unless foreign_currency_code + foreign_amount + exchange_rate are given instead — "
                   "in that case amount is computed automatically.",
    )
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    foreign_currency_code = serializers.CharField(required=False, allow_blank=True, default="")
    foreign_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)
    exchange_rate = serializers.DecimalField(max_digits=14, decimal_places=6, required=False, allow_null=True)

    def validate(self, data):
        has_foreign = data.get("foreign_currency_code") and data.get("foreign_amount") is not None
        if has_foreign and not data.get("exchange_rate"):
            raise serializers.ValidationError("exchange_rate is required when recording a foreign-currency payment.")
        if not has_foreign and data.get("amount") is None:
            raise serializers.ValidationError("amount is required unless recording a foreign-currency payment.")
        return data


class SaleCreateSerializer(serializers.Serializer):
    branch = serializers.UUIDField()
    customer = serializers.UUIDField(required=False, allow_null=True)
    sale_type = serializers.ChoiceField(choices=Sale.SALE_TYPE_CHOICES, default="cash")
    shift = serializers.UUIDField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    tax_total = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    items = SaleItemInputSerializer(many=True)
    payments = PaymentInputSerializer(many=True)
    client_reference = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=64)


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = SaleItem
        fields = ["id", "product", "product_name", "unit", "quantity", "unit_price", "discount_amount", "line_total"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "method", "amount", "reference",
            "foreign_currency_code", "foreign_amount", "exchange_rate_used",
            "reconciliation_status", "reconciled_by", "reconciled_at", "reconciliation_note",
        ]
        read_only_fields = ["id", "reconciled_by", "reconciled_at"]


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "code", "name", "is_active", "sort_order"]
        read_only_fields = ["id", "code"]

    def validate(self, data):
        # 'cash' is protected — see PaymentMethod's docstring for why.
        if self.instance and self.instance.code == "cash" and data.get("is_active") is False:
            raise serializers.ValidationError("The Cash payment method can't be deactivated.")
        return data


class ExchangeRateSerializer(serializers.ModelSerializer):
    set_by_email = serializers.CharField(source="set_by.email", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ["id", "currency_code", "rate_to_business_currency", "set_by", "set_by_email", "created_at"]
        read_only_fields = ["id", "set_by", "created_at"]


class PaymentReconciliationListSerializer(serializers.ModelSerializer):
    """Flattened view for the standalone reconciliation browser —
    includes the sale's transaction number and branch, same reasoning
    as ReceiptPrintLogListSerializer."""
    transaction_number = serializers.CharField(source="sale.transaction_number", read_only=True)
    sale_id = serializers.UUIDField(source="sale.id", read_only=True)
    branch_name = serializers.CharField(source="sale.branch.name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "sale_id", "transaction_number", "branch_name", "method", "amount", "reference",
            "reconciliation_status", "reconciled_by", "reconciled_at", "reconciliation_note", "created_at",
        ]
        read_only_fields = fields


class ReceiptPrintLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptPrintLog
        fields = ["id", "printed_by", "copy_number", "created_at"]


class ReceiptPrintLogListSerializer(serializers.ModelSerializer):
    """Flattened view for the standalone reprint history browser —
    includes the sale's transaction number and branch so it's usable
    without a second lookup per row."""
    transaction_number = serializers.CharField(source="sale.transaction_number", read_only=True)
    sale_id = serializers.UUIDField(source="sale.id", read_only=True)
    branch_name = serializers.CharField(source="sale.branch.name", read_only=True)
    printed_by_email = serializers.EmailField(source="printed_by.email", read_only=True, default=None)

    class Meta:
        model = ReceiptPrintLog
        fields = ["id", "sale_id", "transaction_number", "branch_name", "printed_by_email", "copy_number", "created_at"]
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    print_logs = ReceiptPrintLogSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "transaction_number", "client_reference", "branch", "cashier", "shift", "customer",
            "sale_type", "status",
            "subtotal", "discount_total", "tax_total", "grand_total", "note", "created_at",
            "items", "payments", "print_logs",
        ]
        read_only_fields = fields
