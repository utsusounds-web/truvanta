from decimal import Decimal

from django.test import TestCase

from apps.inventory.models import StockLevel
from tests.factories import make_user, make_business_with_owner, make_product


class TenantIsolationTests(TestCase):
    def test_business_data_is_not_visible_across_tenants(self):
        user_a = make_user("a@example.com")
        user_b = make_user("b@example.com")
        business_a, branch_a = make_business_with_owner(user_a, "Shop A")
        business_b, branch_b = make_business_with_owner(user_b, "Shop B")

        product_a, _ = make_product(business_a, name="Product A")
        product_b, _ = make_product(business_b, name="Product B")

        # Same-named-field lookups scoped to each business must not cross over.
        from apps.products.models import Product
        self.assertEqual(Product.objects.filter(business=business_a).count(), 1)
        self.assertEqual(Product.objects.filter(business=business_b).count(), 1)
        self.assertNotIn(product_b, Product.objects.filter(business=business_a))
        self.assertNotIn(product_a, Product.objects.filter(business=business_b))

    def test_membership_required_for_access(self):
        from apps.accounts.models import Membership
        user_a = make_user("a2@example.com")
        user_b = make_user("b2@example.com")
        business_a, _ = make_business_with_owner(user_a, "Shop A2")

        self.assertTrue(Membership.objects.filter(user=user_a, business=business_a, is_active=True).exists())
        self.assertFalse(Membership.objects.filter(user=user_b, business=business_a, is_active=True).exists())
