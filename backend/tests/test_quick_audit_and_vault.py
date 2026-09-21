from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.stock_audit import services as audit_services
from apps.documents.models import VaultDocument
from tests.factories import make_user, make_business_with_owner, make_product


class QuickAuditTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        for i in range(6):
            product, unit = make_product(self.business, name=f"Product {i}", cost=Decimal("1000"))
            record_movement(business=self.business, product=product, branch=self.branch,
                             quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.user)

    def test_trigger_creates_lines_up_to_sample_size(self):
        audit = audit_services.trigger_quick_audit(business=self.business, branch=self.branch, triggered_by=self.user, sample_size=3)
        self.assertEqual(audit.lines.count(), 3)
        self.assertEqual(audit.status, "pending")

    def test_record_counts_completes_audit_and_computes_difference(self):
        audit = audit_services.trigger_quick_audit(business=self.business, branch=self.branch, triggered_by=self.user, sample_size=2)
        lines = list(audit.lines.all())
        counts = {str(lines[0].id): 8, str(lines[1].id): 10}
        updated = audit_services.record_counts(audit=audit, counts=counts, counted_by=self.user)
        self.assertEqual(updated.status, "completed")
        lines[0].refresh_from_db()
        self.assertEqual(lines[0].difference, Decimal("-2"))
        self.assertEqual(lines[0].estimated_financial_value, Decimal("-2000"))

    def test_partial_counts_leave_audit_pending(self):
        audit = audit_services.trigger_quick_audit(business=self.business, branch=self.branch, triggered_by=self.user, sample_size=2)
        lines = list(audit.lines.all())
        audit_services.record_counts(audit=audit, counts={str(lines[0].id): 10}, counted_by=self.user)
        audit.refresh_from_db()
        self.assertEqual(audit.status, "pending")


class VaultDocumentTests(TestCase):
    def test_document_belongs_to_business(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        doc = VaultDocument.objects.create(
            business=business, branch=branch, category="supplier_invoice",
            title="Invoice #1", file="vault_documents/test.pdf", uploaded_by=user,
        )
        self.assertEqual(VaultDocument.objects.filter(business=business).count(), 1)
        self.assertEqual(doc.category, "supplier_invoice")
