from rest_framework import serializers

from .models import StockLevel, StockMovement, StockTransfer


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = StockLevel
        fields = ["id", "product", "product_name", "branch", "branch_name", "quantity"]
        read_only_fields = fields


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id", "product", "product_name", "branch", "quantity_delta", "reason",
            "reference_note", "source_type", "source_id", "performed_by", "created_at",
            "client_reference",
        ]
        read_only_fields = ["id", "performed_by", "created_at"]


class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    from_branch_name = serializers.CharField(source="from_branch.name", read_only=True)
    to_branch_name = serializers.CharField(source="to_branch.name", read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id", "product", "product_name", "from_branch", "from_branch_name",
            "to_branch", "to_branch_name", "quantity_sent", "quantity_received",
            "status", "note", "sent_by", "received_by", "sent_at", "received_at",
        ]
        read_only_fields = ["id", "quantity_received", "status", "sent_by", "received_by", "sent_at", "received_at"]

    def validate_product(self, product):
        # A bundle has no physical stock of its own — see
        # Product.is_bundle — so it can't be counted, transferred, or
        # received; only its components can be. Letting one through
        # here would create a StockLevel for something that's
        # supposed to be stockless, which sales would then never draw
        # down (create_sale always resolves a bundle to its
        # components), leaving that number to sit there forever,
        # silently wrong.
        if product.is_bundle:
            raise serializers.ValidationError("A bundle can't be transferred directly — transfer its component products instead.")
        return product
