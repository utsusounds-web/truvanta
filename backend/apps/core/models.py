import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Base model with UUID pk and created/updated timestamps.

    All business-data models inherit from this so every record carries
    an immutable id and a reliable audit-relevant timeline.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(TimeStampedModel):
    """Base model for any record that belongs to exactly one Business.

    Enforcing the business FK at this level (rather than ad-hoc per
    model) is what makes tenant isolation checkable/testable in one
    place instead of being re-implemented per module.
    """

    business = models.ForeignKey(
        "tenants.Business",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


class BackupLog(models.Model):
    """One row per database backup attempt (see management command
    `backup_db`). Platform-level, not tied to any one business — this
    is what powers the 'last backed up' indicator in Platform Admin,
    so the person running the deployment is never just hoping backups
    are actually happening."""

    STATUS_CHOICES = [("success", "Success"), ("failed", "Failed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    filename = models.CharField(max_length=255, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    error = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.status} @ {self.started_at}"
