from django.db import models

from apps.core.models import TenantScopedModel


class VaultDocument(TenantScopedModel):
    """Secure storage for supplier invoices, expense receipts, purchase
    documents, and other supporting evidence (spec section 29). Kept
    separate from the per-expense receipt_image field so documents
    that aren't tied to one specific expense (a signed supplier
    contract, a business license) still have a home.
    """

    CATEGORY_CHOICES = [
        ("supplier_invoice", "Supplier Invoice"),
        ("expense_receipt", "Expense Receipt"),
        ("purchase_document", "Purchase Document"),
        ("supporting_evidence", "Supporting Evidence"),
        ("business_document", "Business Document"),
        ("other", "Other"),
    ]

    branch = models.ForeignKey("tenants.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="vault_documents/")
    note = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
