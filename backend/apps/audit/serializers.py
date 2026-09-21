from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source="branch.name", default=None, read_only=True)
    business_name = serializers.CharField(source="business.name", default=None, read_only=True)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "action", "actor", "actor_name", "business", "business_name", "branch", "branch_name",
            "target_type", "object_id", "previous_value", "new_value",
            "reason", "ip_address", "device_info", "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        return obj.actor.get_full_name() or obj.actor.email

    def get_target_type(self, obj):
        return obj.content_type.model if obj.content_type else None
