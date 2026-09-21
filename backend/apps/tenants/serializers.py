from rest_framework import serializers

from .models import Business, Branch, BranchJoinRequest


class BusinessSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    paystack_secret_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    paystack_configured = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id", "name", "slug", "business_type", "logo", "logo_url", "theme_color",
            "address", "phone_number", "email",
            "receipt_header_note", "receipt_footer_note",
            "currency_code", "timezone", "is_active", "owner", "signup_code",
            "support_access_expires_at",
            "notification_whatsapp_number", "notification_email", "ai_addon_enabled",
            "paystack_public_key", "paystack_secret_key", "paystack_configured",
            "away_mode_enabled", "away_mode_discount_threshold_percent",
            "away_mode_refund_threshold_amount", "away_mode_price_change_threshold_percent",
            "default_tax_rate_percent",
        ]
        read_only_fields = ["id", "owner", "slug", "ai_addon_enabled", "signup_code", "support_access_expires_at"]

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url if obj.logo else None

    def get_paystack_configured(self, obj):
        return bool(obj.paystack_public_key and obj.paystack_secret_key)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        membership = getattr(request, "membership", None) if request else None
        # Deliberately NOT `or membership.branch_id is None` — that
        # means "sees every branch's data", not "is owner/admin". See
        # IsOwnerOrAdmin's docstring for the full reasoning; this used
        # to let a branch-unrestricted low-permission staff member see
        # the signup code and fraud-detection tripwire thresholds that
        # are specifically meant to be hidden from staff.
        is_owner_or_admin = bool(membership and membership.role.system_role in ("owner", "admin"))
        if not is_owner_or_admin:
            # Away-mode thresholds are fraud-detection tripwires — a
            # dishonest staff member who knew the exact number could
            # just stay under it. The signup code and support-access
            # window are owner/admin-only tools, not something every
            # cashier needs to see on a business-profile fetch.
            for field in (
                "signup_code", "support_access_expires_at",
                "away_mode_discount_threshold_percent",
                "away_mode_refund_threshold_amount",
                "away_mode_price_change_threshold_percent",
                "notification_whatsapp_number", "notification_email",
            ):
                data.pop(field, None)
        return data


class BranchSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    parent_branch_name = serializers.CharField(source="parent_branch.name", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id", "business", "name", "address", "phone_number", "logo", "logo_url",
            "parent_branch", "parent_branch_name", "is_active", "created_at",
        ]
        read_only_fields = ["id", "business", "created_at"]

    def validate_parent_branch(self, value):
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError("A branch can't be its own parent.")
        return value

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url if obj.logo else None


class BranchJoinRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.CharField(source="requested_by.email", read_only=True)
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BranchJoinRequest
        fields = [
            "id", "business", "branch_name", "status",
            "requested_by", "requested_by_email", "requested_by_name",
            "reviewed_by", "reviewed_at", "created_branch", "created_at",
        ]
        read_only_fields = [
            "id", "business", "status", "requested_by", "reviewed_by",
            "reviewed_at", "created_branch", "created_at",
        ]

    def get_requested_by_name(self, obj):
        return f"{obj.requested_by.first_name} {obj.requested_by.last_name}".strip() or obj.requested_by.email
