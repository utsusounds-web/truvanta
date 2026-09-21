from rest_framework import serializers

from .models import LoanReadinessReport


class LoanReadinessReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanReadinessReport
        fields = ["id", "period_start", "period_end", "generated_by", "snapshot_json", "created_at"]
        read_only_fields = fields
