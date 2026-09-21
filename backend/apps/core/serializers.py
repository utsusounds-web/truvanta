from rest_framework import serializers

from .models import BackupLog


class BackupLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupLog
        fields = ["id", "started_at", "completed_at", "status", "filename", "size_bytes", "error"]
        read_only_fields = fields
