from decimal import Decimal

from django.test import TestCase

from apps.inventory.models import StockLevel
from apps.inventory.services import record_movement
from apps.sales import services as sales_services
from apps.customers.models import Customer, CustomerCreditTransaction
from tests.factories import make_user, make_business_with_owner, make_product


class SalePostingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch = make_business_with_owner(self.user)
        self.product, self.unit = make_product(self.business)
        record_movement(
            business=self.business, product=self.product, branch=self.branch,
            quantity_delta=Decimal("50"), reason="opening_stock", performed_by=self.user,
        )

    def test_cash_sale_deducts_inventory_and_computes_totals(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("3"),
                    "unit_price": Decimal("2500"), "discount_amount": Decimal("100")}],
            payments=[{"method": "cash", "amount": Decimal("7400")}],
        )
        level = StockLevel.objects.get(business=self.business, product=self.product, branch=self.branch)
        self.assertEqual(level.quantity, Decimal("47"))  # 50 - 3
        self.assertEqual(sale.subtotal, Decimal("7500"))
        self.assertEqual(sale.discount_total, Decimal("100"))
        self.assertEqual(sale.grand_total, Decimal("7400"))
        self.assertEqual(sale.print_logs.count(), 1)

    def test_credit_sale_posts_customer_ledger_entry(self):
        customer = Customer.objects.create(business=self.business, name="Jane Doe")
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("2"),
                    "unit_price": Decimal("2500")}],
            payments=[], customer=customer, sale_type="credit",
        )
        entry = CustomerCreditTransaction.objects.get(customer=customer)
        self.assertEqual(entry.amount, Decimal("5000"))
        self.assertEqual(customer.outstanding_balance, Decimal("5000"))

    def test_cancel_sale_reverses_inventory(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("5"),
                    "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("12500")}],
        )
        sales_services.cancel_sale(sale=sale, actor=self.user, reason="Customer changed mind")
        level = StockLevel.objects.get(business=self.business, product=self.product, branch=self.branch)
        self.assertEqual(level.quantity, Decimal("50"))  # fully restored
        sale.refresh_from_db()
        self.assertEqual(sale.status, "cancelled")

    def test_reprint_increments_copy_number_and_flags_reprint(self):
        sale = sales_services.create_sale(
            business=self.business, branch=self.branch, cashier=self.user,
            items=[{"product": self.product, "unit": self.unit, "quantity": Decimal("1"),
                    "unit_price": Decimal("2500")}],
            payments=[{"method": "cash", "amount": Decimal("2500")}],
        )
        log = sales_services.reprint_receipt(sale=sale, actor=self.user)
        self.assertEqual(log.copy_number, 2)
