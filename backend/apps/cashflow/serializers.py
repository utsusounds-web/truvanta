from rest_framework import serializers

from .models import RecurringExpenseSchedule


class RecurringExpenseScheduleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)

    class Meta:
        model = RecurringExpenseSchedule
        fields = ["id", "name", "amount", "day_of_month", "category", "category_name", "branch", "branch_name", "is_active"]
        read_only_fields = ["id"]
