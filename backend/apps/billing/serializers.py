from rest_framework import serializers

from .models import BillingEvent, Feature, FeatureOverride, Plan, Subscription


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ["id", "key", "name", "description", "category", "is_active", "lock_priority", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlanSerializer(serializers.ModelSerializer):
    features = FeatureSerializer(many=True, read_only=True)
    feature_ids = serializers.PrimaryKeyRelatedField(
        source="features", queryset=Feature.objects.all(), many=True, write_only=True, required=False,
    )

    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "description", "price_amount", "currency", "billing_interval",
            "features", "feature_ids", "is_active", "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    features = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id", "business", "business_name", "plan", "status", "current_period_end",
            "cancel_at_period_end", "features", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_features(self, obj):
        if obj.status != "active" or not obj.plan:
            return []
        return list(obj.plan.features.values_list("key", flat=True))


class FeatureOverrideSerializer(serializers.ModelSerializer):
    feature_key = serializers.CharField(source="feature.key", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    granted_by_email = serializers.CharField(source="granted_by.email", read_only=True)

    class Meta:
        model = FeatureOverride
        fields = [
            "id", "business", "business_name", "feature", "feature_key", "is_enabled",
            "note", "granted_by", "granted_by_email", "expires_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "granted_by", "created_at", "updated_at"]


class BillingEventSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = BillingEvent
        fields = ["id", "business", "business_name", "event_type", "paystack_reference", "processed_ok", "error", "created_at"]
        read_only_fields = fields


class SubscribeRequestSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    callback_url = serializers.URLField()
