from rest_framework import serializers

from .models import ContinuitySettings


class ContinuitySettingsSerializer(serializers.ModelSerializer):
    backup_manager_name = serializers.SerializerMethodField()

    class Meta:
        model = ContinuitySettings
        fields = ["id", "is_enabled", "backup_manager", "backup_manager_name", "inactivity_threshold_days"]
        read_only_fields = ["id"]

    def get_backup_manager_name(self, obj):
        if not obj.backup_manager:
            return None
        return obj.backup_manager.get_full_name() or obj.backup_manager.email

    def validate_backup_manager(self, user):
        if user is None:
            return user
        from apps.accounts.models import Membership
        business_id = self.context["request"].business_id
        if not Membership.objects.filter(business_id=business_id, user=user, is_active=True).exists():
            raise serializers.ValidationError("This person doesn't have an active membership on this business.")
        return user
