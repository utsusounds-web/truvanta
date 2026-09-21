from django.db import models

from apps.core.models import TenantScopedModel


class LoanReadinessReport(TenantScopedModel):
    """A point-in-time, immutable snapshot of the business's financial
    health, formatted for a bank or investor rather than the owner —
    this is the differentiator described in the product plan: most
    small traders get turned down for credit not because their
    business is actually unhealthy, but because they can't *prove*
    their numbers to a lender. Truvanta already has clean, audited
    data; this just packages it.

    Deliberately a stored snapshot, not a live recomputation: the
    QR code on the PDF verifies against `snapshot_json` exactly as it
    was the moment this was generated. If it recomputed live data on
    every scan, the numbers would drift as the business keeps trading
    and a lender re-scanning the code a week later would see
    different figures than what's printed — indistinguishable from
    the document having been tampered with. A stored snapshot is the
    only way the verification is actually meaningful. Never edited or
    deleted after creation for the same reason a receipt or a
    JournalEntry never is.
    """
    period_start = models.DateField()
    period_end = models.DateField()
    generated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    snapshot_json = models.JSONField(help_text="Every figure printed on the report, frozen at generation time.")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and LoanReadinessReport.objects.filter(pk=self.pk).exists():
            raise ValueError("A LoanReadinessReport is immutable once generated. Generate a new one instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("A LoanReadinessReport can't be deleted — it may already be in a lender's hands as proof of authenticity.")
