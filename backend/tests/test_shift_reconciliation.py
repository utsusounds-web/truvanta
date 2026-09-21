from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.sales import services as sales_services
from apps.shifts import services as shift_services
from tests.factories import make_user, make_business_with_owner, make_product


class ShiftReconciliationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business)
        record_movement(
            business=self.business, product=self.product, branch=self.branch,
            quantity_delta=Decimal("100"), reason="opening_stock", performed_by=self.user,
        )

    def test_balanced_shift(self):
        shift = shift_services.open_shift(
            business=self.business, branch=self.branch, employee=self.user, opening_cash=Decimal("5000"),
        )
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user, shift=shift,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("2"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("5000")}],
        )
        closed = shift_services.close_shift(shift=shift, closing_physical_cash=Decimal("10000"), actor=self.user)
        self.assertEqual(closed.expected_closing_cash, Decimal("10000"))
        self.assertEqual(closed.result, "balanced")
        self.assertEqual(closed.status, "reviewed")

    def test_cash_short_flagged_neutrally(self):
        shift = shift_services.open_shift(
            business=self.business, branch=self.branch, employee=self.user, opening_cash=Decimal("5000"),
        )
        closed = shift_services.close_shift(shift=shift, closing_physical_cash=Decimal("4700"), actor=self.user)
        self.assertEqual(closed.variance, Decimal("-300"))
        self.assertEqual(closed.result, "short")

    def test_large_variance_requires_review(self):
        shift = shift_services.open_shift(
            business=self.business, branch=self.branch, employee=self.user, opening_cash=Decimal("5000"),
        )
        closed = shift_services.close_shift(shift=shift, closing_physical_cash=Decimal("1000"), actor=self.user)
        self.assertEqual(closed.result, "requires_review")
        self.assertEqual(closed.status, "pending_review")
