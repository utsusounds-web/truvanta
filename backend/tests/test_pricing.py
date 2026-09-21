from decimal import Decimal

from django.test import TestCase

from apps.products import services as product_services
from apps.products.models import PriceHistory
from apps.inventory.services import record_movement
from apps.reports import services as report_services
from tests.factories import make_user, make_business_with_owner, make_product


class ProductProfitComputationTests(TestCase):
    def test_profit_fields_reflect_gain_and_loss(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        gaining, _ = make_product(business, name="Gainer", cost=Decimal("1000"), price=Decimal("1500"))
        losing, _ = make_product(business, name="Loser", cost=Decimal("2000"), price=Decimal("1500"))

        self.assertEqual(gaining.profit_amount, Decimal("500"))
        self.assertFalse(gaining.is_at_loss)
        self.assertEqual(losing.profit_amount, Decimal("-500"))
        self.assertTrue(losing.is_at_loss)


class PriceRebalancingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, _ = make_product(self.business, cost=Decimal("1000"), price=Decimal("1500"))  # 33.3% margin

    def test_suggested_price_preserves_margin_when_cost_rises(self):
        suggested = product_services.suggest_rebalanced_price(self.product, Decimal("1200"))
        # margin ratio ~0.3333 -> suggested = 1200 / (1 - 0.3333) ~= 1800
        self.assertGreater(suggested, Decimal("1799"))
        self.assertLess(suggested, Decimal("1802"))

    def test_update_cost_price_creates_history_and_audit(self):
        product_services.update_cost_price(
            product=self.product, new_cost_price=Decimal("1200"), actor=self.user,
            new_selling_price=Decimal("1800"), reason="Supplier raised prices",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.cost_price, Decimal("1200"))
        self.assertEqual(self.product.selling_price, Decimal("1800"))
        history = PriceHistory.objects.get(product=self.product)
        self.assertEqual(history.old_cost_price, Decimal("1000"))
        self.assertEqual(history.new_cost_price, Decimal("1200"))

    def test_cost_price_update_without_selling_change_can_create_a_loss(self):
        # Cost rises above the unchanged selling price -> now at a loss.
        product_services.update_cost_price(
            product=self.product, new_cost_price=Decimal("1600"), actor=self.user,
        )
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_at_loss)


class InventoryProfitabilityReportTests(TestCase):
    def test_report_flags_at_loss_and_totals_correctly(self):
        user = make_user()
        business, branch = make_business_with_owner(user)
        healthy, _ = make_product(business, name="Healthy", cost=Decimal("1000"), price=Decimal("1500"))
        at_loss, _ = make_product(business, name="AtLoss", cost=Decimal("2000"), price=Decimal("1500"))
        record_movement(business=business, product=healthy, branch=branch, quantity_delta=Decimal("10"),
                         reason="opening_stock", performed_by=user)
        record_movement(business=business, product=at_loss, branch=branch, quantity_delta=Decimal("5"),
                         reason="opening_stock", performed_by=user)

        report = report_services.inventory_profitability(business=business, branch=branch)
        self.assertEqual(report["total_cost_value"], Decimal("10") * 1000 + Decimal("5") * 2000)
        self.assertEqual(len(report["products_at_loss"]), 1)
        self.assertEqual(report["products_at_loss"][0]["product_name"], "AtLoss")
