from decimal import Decimal

from django.test import TestCase

from apps.inventory.services import record_movement
from apps.products import services as product_services
from apps.sales import services as sales_services
from apps.sales.models import SaleItem
from apps.returns.models import SaleReturn
from apps.returns import services as return_services
from apps.notifications.models import Notification
from tests.factories import make_user, make_business_with_owner, make_product


class AwayModeDiscountTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.business.away_mode_enabled = True
        self.business.away_mode_discount_threshold_percent = Decimal("20")
        self.business.save()
        self.product, self.unit = make_product(self.business, price=Decimal("1000"))
        record_movement(business=self.business, product=self.product, branch=self.branch,
                         quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.user)

    def test_discount_above_threshold_triggers_critical_alert(self):
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"),
                    "unit_price": Decimal("1000"), "discount_amount": Decimal("300")}],  # 30% > 20% threshold
            payments=[{"method": "cash", "amount": Decimal("700")}],
        )
        self.assertTrue(Notification.objects.filter(business=self.business, level="critical", title__icontains="Large discount").exists())

    def test_discount_below_threshold_does_not_alert(self):
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"),
                    "unit_price": Decimal("1000"), "discount_amount": Decimal("100")}],  # 10% < 20%
            payments=[{"method": "cash", "amount": Decimal("900")}],
        )
        self.assertFalse(Notification.objects.filter(business=self.business, level="critical", title__icontains="Large discount").exists())

    def test_disabled_away_mode_never_alerts_regardless_of_discount_size(self):
        self.business.away_mode_enabled = False
        self.business.save()
        sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"),
                    "unit_price": Decimal("1000"), "discount_amount": Decimal("900")}],  # 90%!
            payments=[{"method": "cash", "amount": Decimal("100")}],
        )
        self.assertFalse(Notification.objects.filter(business=self.business, level="critical").exists())


class AwayModePriceChangeTests(TestCase):
    def test_large_cost_change_triggers_alert(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        business.away_mode_enabled = True
        business.away_mode_price_change_threshold_percent = Decimal("10")
        business.save()
        product, unit = make_product(business, cost=Decimal("1000"), price=Decimal("1500"))

        product_services.update_cost_price(product=product, new_cost_price=Decimal("1300"), actor=user)  # 30% jump
        self.assertTrue(Notification.objects.filter(business=business, level="critical", title__icontains="price change").exists())


class AwayModeRefundTests(TestCase):
    def test_large_refund_request_triggers_immediate_alert(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        business.away_mode_enabled = True
        business.away_mode_refund_threshold_amount = Decimal("5000")
        business.save()
        product, unit = make_product(business, price=Decimal("10000"))
        record_movement(business=business, product=product, branch=branch, quantity_delta=Decimal("5"),
                         reason="opening_stock", performed_by=user)
        sale = sales_services.create_sale(
            business=business, branch=branch, cashier=user,
            items=[{"product": product, "unit": unit, "quantity": Decimal("1"), "unit_price": Decimal("10000")}],
            payments=[{"method": "cash", "amount": Decimal("10000")}],
        )
        sale_item = sale.items.first()
        sale_return = SaleReturn.objects.create(
            business=business, sale=sale, sale_item=sale_item, return_type="refund",
            quantity=Decimal("1"), refund_amount=Decimal("8000"), reason="Customer complaint",
        )
        return_services.notify_if_large_refund_while_away(sale_return)
        self.assertTrue(Notification.objects.filter(business=business, level="critical", title__icontains="refund").exists())
