from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, Membership, Permission, RolePermission
from apps.tenants.models import Branch
from apps.inventory.services import record_movement
from tests.factories import make_user, make_business_with_owner, make_product


def grant(role, *codes):
    for code in codes:
        perm, _ = Permission.objects.get_or_create(code=code, defaults={"label": code})
        RolePermission.objects.get_or_create(role=role, permission=perm)


class BranchAccessEnforcementTests(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.business, self.branch_a = make_business_with_owner(self.owner)
        self.branch_b = Branch.objects.create(business=self.business, name="Branch B")
        self.product, self.unit = make_product(self.business)

        self.cashier_role = Role.objects.create(business=self.business, name="Cashier", system_role="cashier")
        self.cashier = make_user(email="cashier@example.com")
        Membership.objects.create(
            user=self.cashier, business=self.business, branch=self.branch_a, role=self.cashier_role,
        )

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.cashier_client = APIClient()
        self.cashier_client.force_authenticate(user=self.cashier)
        self.headers = {"HTTP_X_BUSINESS_ID": str(self.business.id)}

    def test_owner_sees_every_branch(self):
        r = self.owner_client.get("/api/tenants/branches/", **self.headers)
        names = {b["name"] for b in r.data["results"]}
        self.assertEqual(names, {"Main Branch", "Branch B"})

    def test_branch_restricted_staff_only_sees_their_branch(self):
        r = self.cashier_client.get("/api/tenants/branches/", **self.headers)
        names = {b["name"] for b in r.data["results"]}
        self.assertEqual(names, {"Main Branch"})

    def test_branch_restricted_staff_cannot_open_shift_on_other_branch(self):
        r = self.cashier_client.post(
            "/api/shifts/", {"branch": str(self.branch_b.id), "opening_cash": "10000"}, **self.headers
        )
        self.assertEqual(r.status_code, 403)

    def test_branch_restricted_staff_can_open_shift_on_own_branch(self):
        r = self.cashier_client.post(
            "/api/shifts/", {"branch": str(self.branch_a.id), "opening_cash": "10000"}, **self.headers
        )
        self.assertEqual(r.status_code, 201)

    def test_branch_restricted_staff_cannot_see_other_branchs_sales(self):
        record_movement(
            business=self.business, product=self.product, branch=self.branch_b,
            quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.owner,
        )
        sale_payload = {
            "branch": str(self.branch_b.id), "customer": None, "sale_type": "cash", "shift": None,
            "tax_total": 0,
            "items": [{"product": str(self.product.id), "unit": str(self.unit.id), "quantity": 1, "unit_price": 2500, "discount_amount": 0}],
            "payments": [{"method": "cash", "amount": 2500}],
        }
        r = self.owner_client.post("/api/sales/", sale_payload, format="json", **self.headers)
        self.assertEqual(r.status_code, 201, r.data)
        sale_id = r.data["id"]

        listed = self.cashier_client.get("/api/sales/", **self.headers)
        self.assertNotIn(sale_id, [s["id"] for s in listed.data["results"]])

        detail = self.cashier_client.get(f"/api/sales/{sale_id}/", **self.headers)
        self.assertEqual(detail.status_code, 404)

    def test_branch_restricted_staff_cannot_record_stock_movement_elsewhere(self):
        grant(self.cashier_role, "manage_inventory")
        r = self.cashier_client.post("/api/stock-movements/", {
            "product": str(self.product.id), "branch": str(self.branch_b.id),
            "quantity_delta": 5, "reason": "adjustment", "reference_note": "count fix",
        }, **self.headers)
        self.assertEqual(r.status_code, 403)

    def test_membership_with_no_branch_sees_everything(self):
        manager_role = Role.objects.create(business=self.business, name="Manager", system_role="admin")
        manager = make_user(email="manager@example.com")
        Membership.objects.create(user=manager, business=self.business, branch=None, role=manager_role)
        client = APIClient()
        client.force_authenticate(user=manager)
        r = client.get("/api/tenants/branches/", **self.headers)
        names = {b["name"] for b in r.data["results"]}
        self.assertEqual(names, {"Main Branch", "Branch B"})

    def test_mini_branch_access_inherits_from_accessible_main_branch(self):
        mini = Branch.objects.create(business=self.business, name="Kiosk under A", parent_branch=self.branch_a)
        r = self.cashier_client.get("/api/tenants/branches/", **self.headers)
        names = {b["name"] for b in r.data["results"]}
        self.assertEqual(names, {"Main Branch", "Kiosk under A"})
        shift_r = self.cashier_client.post(
            "/api/shifts/", {"branch": str(mini.id), "opening_cash": "5000"}, **self.headers
        )
        self.assertEqual(shift_r.status_code, 201)


class GranularPermissionEnforcementTests(TestCase):
    """A role with no explicit RolePermission grants can read what it
    needs to function, but can't perform the sensitive actions the
    spec says should require an explicit grant — cancelling sales,
    approving expenses/returns, managing staff/products/inventory/
    suppliers, or seeing profit figures."""

    def setUp(self):
        self.owner = make_user()
        self.business, self.branch = make_business_with_owner(self.owner)
        self.product, self.unit = make_product(self.business)
        self.cashier_role = Role.objects.create(business=self.business, name="Cashier", system_role="cashier")
        self.cashier = make_user(email="cashier@example.com")
        Membership.objects.create(user=self.cashier, business=self.business, branch=None, role=self.cashier_role)

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.cashier_client = APIClient()
        self.cashier_client.force_authenticate(user=self.cashier)
        self.headers = {"HTTP_X_BUSINESS_ID": str(self.business.id)}

    def test_owner_bypasses_all_permission_checks(self):
        r = self.owner_client.get("/api/reports/where-did-my-money-go/", **self.headers)
        self.assertNotEqual(r.status_code, 403)

    def test_cashier_without_grant_cannot_view_profit_report(self):
        r = self.cashier_client.get("/api/reports/where-did-my-money-go/", **self.headers)
        self.assertEqual(r.status_code, 403)

    def test_cashier_with_grant_can_view_profit_report(self):
        grant(self.cashier_role, "view_profit")
        r = self.cashier_client.get("/api/reports/where-did-my-money-go/", **self.headers)
        self.assertNotEqual(r.status_code, 403)

    def test_cashier_without_grant_cannot_create_role(self):
        r = self.cashier_client.post(
            "/api/auth/roles/", {"name": "New Role"}, format="json", **self.headers
        )
        self.assertEqual(r.status_code, 403)

    def test_cashier_can_still_list_roles_without_grant(self):
        r = self.cashier_client.get("/api/auth/roles/", **self.headers)
        self.assertEqual(r.status_code, 200)

    def test_cashier_without_grant_cannot_cancel_sale(self):
        record_movement(
            business=self.business, product=self.product, branch=self.branch,
            quantity_delta=Decimal("10"), reason="opening_stock", performed_by=self.owner,
        )
        sale_payload = {
            "branch": str(self.branch.id), "customer": None, "sale_type": "cash", "shift": None,
            "tax_total": 0,
            "items": [{"product": str(self.product.id), "unit": str(self.unit.id), "quantity": 1, "unit_price": 2500, "discount_amount": 0}],
            "payments": [{"method": "cash", "amount": 2500}],
        }
        r = self.owner_client.post("/api/sales/", sale_payload, format="json", **self.headers)
        sale_id = r.data["id"]
        cancel = self.cashier_client.post(f"/api/sales/{sale_id}/cancel/", {"reason": "test"}, **self.headers)
        self.assertEqual(cancel.status_code, 403)

    def test_cashier_without_grant_cannot_create_product(self):
        r = self.cashier_client.post("/api/products/", {
            "name": "New Product", "sku": "", "barcode": "",
            "cost_price": "100", "selling_price": "150",
            "reorder_level": "0", "base_unit": str(self.unit.id),
        }, format="multipart", **self.headers)
        self.assertEqual(r.status_code, 403)

    def test_cashier_can_still_list_products_without_grant(self):
        r = self.cashier_client.get("/api/products/", **self.headers)
        self.assertEqual(r.status_code, 200)

    def test_cashier_without_grant_cannot_create_supplier(self):
        r = self.cashier_client.post(
            "/api/suppliers/", {"name": "Acme Supplies"}, format="json", **self.headers
        )
        self.assertEqual(r.status_code, 403)
