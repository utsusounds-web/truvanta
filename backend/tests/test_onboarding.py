from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TestCase

from apps.accounts.models import User
from apps.products.models import UnitOfMeasure


class OnboardingSeedTests(TestCase):
    def test_new_business_starts_with_selectable_units(self):
        """Regression test: a brand-new business must have at least one
        UnitOfMeasure so the product form's unit dropdown is never a
        dead end for a first-time owner (see tenants.views._seed_default_units)."""
        user = User.objects.create_user(username="seedtest", email="seedtest@example.com", password="StrongPass123!")
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.post("/api/tenants/businesses/", {
            "name": "Seed Test Shop", "business_type": "retail",
            "currency_code": "NGN", "timezone": "Africa/Lagos",
        }, format="multipart")

        self.assertEqual(response.status_code, 201)
        business_id = response.data["business"]["id"]
        units = UnitOfMeasure.objects.filter(business_id=business_id)
        self.assertGreater(units.count(), 0)
        self.assertIn("Piece", list(units.values_list("name", flat=True)))
