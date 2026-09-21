import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    """Immutable record of a sensitive action.

    Rows are never updated or deleted by application code — corrections
    to business data happen via new, linked audit-visible actions
    (e.g. a reversing entry), never by editing history. Uses a generic
    FK so any model (Sale, StockMovement, Expense, Membership, ...)
    can be the subject without audit needing to know about it upfront.
    """

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("price_change", "Price Change"),
        ("discount", "Discount Applied"),
        ("refund", "Refund"),
        ("return", "Return"),
        ("cancellation", "Cancellation"),
        ("stock_adjustment", "Stock Adjustment"),
        ("expense_change", "Expense Change"),
        ("credit_change", "Credit Change"),
        ("permission_change", "Permission Change"),
        ("login", "Login"),
        ("login_failed", "Failed Login"),
        ("receipt_reprint", "Receipt Reprint"),
        ("shift_event", "Shift Event"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        "tenants.Business", on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True,
    )
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs",
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    previous_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    new_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    reason = models.CharField(max_length=500, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "action", "created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"[{self.business_id}] {self.action} by {self.actor_id} @ {self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog entries are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog entries cannot be deleted.")
