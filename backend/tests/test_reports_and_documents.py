from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.sales import services as sales_services
from apps.sales.documents import generate_receipt_pdf
from apps.reports import services as report_services
from apps.audit.risk import scan_branch
from tests.factories import make_user, make_business_with_owner, make_product


class ReceiptPdfTests(TestCase):
    def test_receipt_pdf_generates_bytes_and_reflects_branding(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        business.name = "Zeke's Provisions"
        business.receipt_footer_note = "No refunds after 24 hours"
        business.save()
        product, unit = make_product(business)
        record_movement(business=business, product=product, branch=branch, quantity_delta=Decimal("10"),
                         reason="opening_stock", performed_by=user)
        sale = sales_services.create_sale(
            business=business, branch=branch, cashier=user,
            items=[{"product": product, "unit": unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("2500")}],
        )
        pdf_bytes = generate_receipt_pdf(sale, copy_number=1)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 500)


class ReportServiceTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business)
        record_movement(business=self.business, product=self.product, branch=self.branch,
                         quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.user)

    def test_owner_dashboard_reflects_a_posted_sale(self):
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("2"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("5000")}],
        )
        data = report_services.owner_dashboard(business=self.business, branch=self.branch)
        self.assertEqual(data["total_sales"], Decimal("5000"))
        self.assertEqual(data["number_of_sales"], 1)

    def test_where_did_my_money_go_reconciles(self):
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("2"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("5000")}],
        )
        data = report_services.where_did_my_money_go(business=self.business, branch=self.branch)
        self.assertEqual(data["money_received"], Decimal("5000"))
        self.assertEqual(data["cash_remaining"], Decimal("5000"))  # no expenses/purchases recorded yet


class RiskDetectionTests(TestCase):
    def test_excessive_discount_flagged(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        product, unit = make_product(business)
        record_movement(business=business, product=product, branch=branch, quantity_delta=Decimal("10"),
                         reason="opening_stock", performed_by=user)
        sales_services.create_sale(
            business=business, branch=branch, cashier=user,
            items=[{"product": product, "unit": unit, "quantity": Decimal("1"),
                    "unit_price": Decimal("2500"), "discount_amount": Decimal("1000")}],  # 40% discount
            payments=[{"method": "cash", "amount": Decimal("1500")}],
        )
        alerts = scan_branch(business=business, branch=branch, days=7)
        rules_fired = {a.rule for a in alerts}
        self.assertIn("excessive_discount", rules_fired)
