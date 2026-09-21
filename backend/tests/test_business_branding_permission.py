from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, Membership
from tests.factories import make_user, make_business_with_owner


class BusinessBrandingPermissionTests(TestCase):
    """Changing the business logo/branding (Settings page) must be
    owner/admin only — a plain staff member with business-level
    membership should be able to view the profile (the logo needs to
    render for everyone) but never change it."""

    def setUp(self):
        self.owner = make_user()
        self.business, self.branch = make_business_with_owner(self.owner)

        self.cashier_role = Role.objects.create(business=self.business, name="Cashier", system_role="cashier")
        self.cashier = make_user(email="cashier@example.com")
        Membership.objects.create(
            user=self.cashier, business=self.business, branch=self.branch, role=self.cashier_role,
        )

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.cashier_client = APIClient()
        self.cashier_client.force_authenticate(user=self.cashier)
        self.headers = {"HTTP_X_BUSINESS_ID": str(self.business.id)}
        self.url = f"/api/tenants/businesses/{self.business.id}/"

    def test_any_member_can_view_business_profile(self):
        r = self.cashier_client.get(self.url, **self.headers)
        self.assertEqual(r.status_code, 200)

    def test_cashier_cannot_change_business_name_or_logo(self):
        r = self.cashier_client.patch(self.url, {"name": "Hijacked Name"}, format="multipart", **self.headers)
        self.assertEqual(r.status_code, 403)
        self.business.refresh_from_db()
        self.assertNotEqual(self.business.name, "Hijacked Name")

    def test_owner_can_change_business_name(self):
        r = self.owner_client.patch(self.url, {"name": "Renamed Shop"}, format="multipart", **self.headers)
        self.assertEqual(r.status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Renamed Shop")
