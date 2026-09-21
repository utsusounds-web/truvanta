from rest_framework import serializers

from .models import Account, JournalEntry, JournalLine, OpeningBalanceStatement


class OpeningBalanceStatementSerializer(serializers.ModelSerializer):
    total_assets = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_liabilities = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    net_worth = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OpeningBalanceStatement
        fields = [
            "id", "as_of_date", "cash_on_hand", "bank_balance", "accounts_receivable",
            "inventory_value", "fixed_assets", "accounts_payable", "loans_payable",
            "total_assets", "total_liabilities", "net_worth",
            "recorded_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "total_assets", "total_liabilities", "net_worth", "recorded_by_name", "created_at", "updated_at"]

    def get_recorded_by_name(self, obj):
        if not obj.recorded_by:
            return None
        full_name = f"{obj.recorded_by.first_name} {obj.recorded_by.last_name}".strip()
        return full_name or obj.recorded_by.email


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "code", "name", "account_type", "is_active"]
        read_only_fields = fields


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = ["id", "account", "account_code", "account_name", "debit", "credit"]
        read_only_fields = fields


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id", "entry_date", "description", "source_type", "source_id",
            "reverses", "branch", "lines", "created_at",
        ]
        read_only_fields = fields
