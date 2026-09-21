from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.sales import services as sales_services
from apps.shifts import services as shift_services
from apps.notifications.models import Notification
from tests.factories import make_user, make_business_with_owner, make_product


class OfflineIdempotencyTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business)
        record_movement(business=self.business, product=self.product, branch=self.branch,
                         quantity_delta=Decimal("50"), reason="opening_stock", performed_by=self.user)

    def test_retrying_a_queued_sale_with_same_reference_does_not_duplicate(self):
        payload = dict(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("2"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("5000")}],
            client_reference="offline-abc-123",
        )
        sale1 = sales_services.create_sale(**payload)
        sale2 = sales_services.create_sale(**payload)  # simulates a retried sync after a flaky connection
        self.assertEqual(sale1.id, sale2.id)
        self.assertEqual(sale1.transaction_number, sale2.transaction_number)

        from apps.sales.models import Sale
        self.assertEqual(Sale.objects.filter(business=self.business).count(), 1)

    def test_different_offline_sales_with_different_references_both_post(self):
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("2500")}], client_reference="offline-1",
        )
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("2500")}], client_reference="offline-2",
        )
        from apps.sales.models import Sale
        self.assertEqual(Sale.objects.filter(business=self.business).count(), 2)


class NotificationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business, reorder_level=10)
        record_movement(business=self.business, product=self.product, branch=self.branch,
                         quantity_delta=Decimal("12"), reason="opening_stock", performed_by=self.user)

    def test_low_stock_after_sale_creates_notification_record(self):
        # No WhatsApp/email configured in test settings -> delivery no-ops,
        # but the Notification row must still be created (in-app history).
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("5"), "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("12500")}],
        )
        notif = Notification.objects.filter(business=self.business, level="important").first()
        self.assertIsNotNone(notif)
        self.assertIn("Low stock", notif.title)
        self.assertFalse(notif.whatsapp_delivered)
        self.assertFalse(notif.email_delivered)

    def test_shift_requiring_review_creates_critical_notification(self):
        shift = shift_services.open_shift(business=self.business, branch=self.branch, employee=self.user, opening_cash=Decimal("5000"))
        shift_services.close_shift(shift=shift, closing_physical_cash=Decimal("500"), actor=self.user)
        notif = Notification.objects.filter(business=self.business, level="critical").first()
        self.assertIsNotNone(notif)
        self.assertIn("variance", notif.title.lower())


class StockMovementIdempotencyTests(TestCase):
    def test_retrying_a_queued_adjustment_with_same_reference_does_not_duplicate(self):
        from apps.inventory.services import record_movement
        from apps.inventory.models import StockMovement

        user = make_user()
        business, branch = make_business_with_owner(user)
        product, unit = make_product(business)

        kwargs = dict(
            business=business, product=product, branch=branch, quantity_delta=Decimal("10"),
            reason="opening_stock", performed_by=user, client_reference="offline-adj-1",
        )
        m1 = record_movement(**kwargs)
        m2 = record_movement(**kwargs)  # simulated retry after a flaky sync
        self.assertEqual(m1.id, m2.id)
        self.assertEqual(StockMovement.objects.filter(business=business).count(), 1)
