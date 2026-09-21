from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.sales import services as sales_services
from apps.sales.models import Payment
from tests.factories import make_user, make_business_with_owner, make_product


class PaymentReconciliationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business)
        record_movement(business=self.business, product=self.product, branch=self.branch,
                         quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.user)

    def test_cash_payment_is_automatically_confirmed(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("2500")}],
        )
        payment = sale.payments.first()
        self.assertEqual(payment.reconciliation_status, "confirmed")
        self.assertIsNone(payment.reconciled_by)  # auto-confirmed, not by a person

    def test_bank_transfer_payment_starts_pending(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "bank_transfer", "amount": Decimal("2500"), "reference": "TXN123"}],
        )
        payment = sale.payments.first()
        self.assertEqual(payment.reconciliation_status, "pending")

    def test_card_payment_starts_pending(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "card", "amount": Decimal("2500")}],
        )
        payment = sale.payments.first()
        self.assertEqual(payment.reconciliation_status, "pending")
