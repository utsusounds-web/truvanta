from rest_framework import serializers
from .models import Notification, PlatformSettings


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "branch", "level", "title", "message", "link_path", "created_at",
            "whatsapp_attempted", "whatsapp_delivered", "whatsapp_error",
            "email_attempted", "email_delivered", "email_error",
            "is_read", "read_at",
        ]
        read_only_fields = ["id", "branch", "level", "title", "message", "link_path", "created_at",
            "whatsapp_attempted", "whatsapp_delivered", "whatsapp_error",
            "email_attempted", "email_delivered", "email_error", "read_at"]

    def update(self, instance, validated_data):
        # read_at is server-controlled, not client-writable — set the
        # instant it's actually marked read here, rather than trust
        # whatever timestamp (or lack of one) the client sends.
        if validated_data.get("is_read") and not instance.is_read:
            from django.utils import timezone
            instance.read_at = timezone.now()
        elif "is_read" in validated_data and not validated_data["is_read"]:
            instance.read_at = None
        return super().update(instance, validated_data)


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """Secrets (tokens/passwords/keys) are write-only — the frontend
    can set them but a GET never echoes them back, same principle as
    a password field. `*_is_set` booleans let the UI show 'configured'
    without ever exposing the value."""

    whatsapp_access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email_host_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    platform_paystack_secret_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    whatsapp_configured = serializers.SerializerMethodField()
    email_configured = serializers.SerializerMethodField()
    paystack_configured = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSettings
        fields = [
            "whatsapp_access_token", "whatsapp_phone_number_id", "whatsapp_configured",
            "email_host_user", "email_host_password", "email_configured",
            "platform_paystack_public_key", "platform_paystack_secret_key", "paystack_configured",
            "rent_mode_enabled", "universal_color", "minimum_client_version", "google_oauth_client_id",
            "trial_grace_days", "trial_grace_feature_count", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_whatsapp_configured(self, obj):
        return bool(obj.whatsapp_access_token and obj.whatsapp_phone_number_id)

    def get_email_configured(self, obj):
        return bool(obj.email_host_user and obj.email_host_password)

    def get_paystack_configured(self, obj):
        return bool(obj.platform_paystack_public_key and obj.platform_paystack_secret_key)
