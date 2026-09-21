from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.customers.models import Customer, CustomerCreditTransaction
from apps.inventory.services import record_movement
from apps.notifications import triggers
from apps.notifications.models import Notification
from apps.sales import services as sales_services
from tests.factories import make_user, make_business_with_owner, make_product


class OverdueDebtTriggerTests(TestCase):
    def test_overdue_credit_triggers_one_summary_notification(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        customer = Customer.objects.create(business=business, name="Late Payer")
        CustomerCreditTransaction.objects.create(
            business=business, customer=customer, entry_type="credit_sale", amount=Decimal("5000"),
            due_date=date.today() - timedelta(days=5),
        )
        result = triggers.check_overdue_debts(business)
        self.assertIsNotNone(result)
        self.assertEqual(Notification.objects.filter(business=business, level="important").count(), 1)
        self.assertIn("Late Payer", result.message)

    def test_no_overdue_debt_returns_none_and_creates_nothing(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        result = triggers.check_overdue_debts(business)
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.filter(business=business).count(), 0)

    def test_paid_off_overdue_customer_is_not_flagged(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        customer = Customer.objects.create(business=business, name="Paid Up")
        CustomerCreditTransaction.objects.create(
            business=business, customer=customer, entry_type="credit_sale", amount=Decimal("5000"),
            due_date=date.today() - timedelta(days=5),
        )
        CustomerCreditTransaction.objects.create(
            business=business, customer=customer, entry_type="payment", amount=Decimal("-5000"),
        )
        result = triggers.check_overdue_debts(business)
        self.assertIsNone(result)


class DailySummaryTriggerTests(TestCase):
    def test_summary_reflects_todays_sales(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        product, unit = make_product(business)
        record_movement(business=business, product=product, branch=branch, quantity_delta=Decimal("10"),
                         reason="opening_stock", performed_by=user)
        sales_services.create_sale(
            business=business, branch=branch, cashier=user,
            items=[{"product": product, "unit": unit, "quantity": Decimal("2"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("5000")}],
        )
        result = triggers.send_daily_summary(business, branch)
        self.assertIn("5000", result.message)
        self.assertEqual(result.level, "info")
