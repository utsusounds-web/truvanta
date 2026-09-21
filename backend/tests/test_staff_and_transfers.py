from decimal import Decimal

from django.test import TestCase

from apps.accounts import services as account_services
from apps.accounts.models import Role, Membership, Permission
from apps.inventory import services as inventory_services
from apps.inventory.models import StockLevel, StockTransfer
from tests.factories import make_user, make_business_with_owner, make_product


class StaffManagementTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@shop.test")
        self.business, self.branch = make_business_with_owner(self.owner)
        self.staff_user = make_user("cashier@shop.test")
        self.cashier_role = Role.objects.create(business=self.business, name="Cashier", system_role="cashier")

    def test_invite_existing_user_creates_membership(self):
        membership = account_services.invite_staff_member(
            business=self.business, branch=self.branch, email="cashier@shop.test",
            role=self.cashier_role, invited_by=self.owner,
        )
        self.assertEqual(membership.user, self.staff_user)
        self.assertTrue(Membership.objects.filter(user=self.staff_user, business=self.business).exists())

    def test_invite_unknown_email_raises(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            account_services.invite_staff_member(
                business=self.business, branch=self.branch, email="nobody@nowhere.test",
                role=self.cashier_role, invited_by=self.owner,
            )

    def test_deactivate_membership_revokes_access(self):
        membership = account_services.invite_staff_member(
            business=self.business, branch=self.branch, email="cashier@shop.test",
            role=self.cashier_role, invited_by=self.owner,
        )
        account_services.deactivate_membership(membership=membership, actor=self.owner)
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertFalse(membership.has_permission("manage_inventory"))

    def test_role_permission_grants_specific_access(self):
        membership = account_services.invite_staff_member(
            business=self.business, branch=self.branch, email="cashier@shop.test",
            role=self.cashier_role, invited_by=self.owner,
        )
        self.assertFalse(membership.has_permission("approve_expenses"))
        perm = Permission.objects.get(code="approve_expenses")
        from apps.accounts.models import RolePermission
        RolePermission.objects.create(role=self.cashier_role, permission=perm)
        self.assertTrue(membership.has_permission("approve_expenses"))

    def test_owner_role_has_all_permissions_implicitly(self):
        owner_membership = Membership.objects.get(user=self.owner, business=self.business)
        self.assertTrue(owner_membership.has_permission("anything_at_all"))


class StockTransferTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.business, self.branch_a = make_business_with_owner(self.user)
        from apps.tenants.models import Branch
        self.branch_b = Branch.objects.create(business=self.business, name="Branch B")
        self.product, self.unit = make_product(self.business)
        inventory_services.record_movement(
            business=self.business, product=self.product, branch=self.branch_a,
            quantity_delta=Decimal("20"), reason="opening_stock", performed_by=self.user,
        )

    def test_send_transfer_deducts_from_sending_branch_immediately(self):
        transfer = inventory_services.send_transfer(
            business=self.business, product=self.product, from_branch=self.branch_a,
            to_branch=self.branch_b, quantity=Decimal("5"), sent_by=self.user,
        )
        level_a = StockLevel.objects.get(business=self.business, product=self.product, branch=self.branch_a)
        self.assertEqual(level_a.quantity, Decimal("15"))
        self.assertEqual(transfer.status, "pending")

    def test_full_receipt_matches_and_closes_clean(self):
        transfer = inventory_services.send_transfer(
            business=self.business, product=self.product, from_branch=self.branch_a,
            to_branch=self.branch_b, quantity=Decimal("5"), sent_by=self.user,
        )
        updated = inventory_services.receive_transfer(transfer=transfer, quantity_received=Decimal("5"), received_by=self.user)
        self.assertEqual(updated.status, "received")
        level_b = StockLevel.objects.get(business=self.business, product=self.product, branch=self.branch_b)
        self.assertEqual(level_b.quantity, Decimal("5"))

    def test_short_receipt_flags_discrepancy_and_does_not_fabricate_stock(self):
        transfer = inventory_services.send_transfer(
            business=self.business, product=self.product, from_branch=self.branch_a,
            to_branch=self.branch_b, quantity=Decimal("5"), sent_by=self.user,
        )
        updated = inventory_services.receive_transfer(transfer=transfer, quantity_received=Decimal("3"), received_by=self.user)
        self.assertEqual(updated.status, "received_with_discrepancy")
        level_b = StockLevel.objects.get(business=self.business, product=self.product, branch=self.branch_b)
        self.assertEqual(level_b.quantity, Decimal("3"))  # only what actually arrived, never backfilled to match sent


class MembershipUpdateTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner2@shop.test")
        self.business, self.branch = make_business_with_owner(self.owner)
        self.staff_user = make_user("staffmember@shop.test")
        self.role_a = Role.objects.create(business=self.business, name="Cashier A")
        self.role_b = Role.objects.create(business=self.business, name="Cashier B")
        self.membership = account_services.invite_staff_member(
            business=self.business, branch=self.branch, email="staffmember@shop.test",
            role=self.role_a, invited_by=self.owner,
        )

    def test_deactivate_then_reactivate_round_trips_cleanly(self):
        account_services.deactivate_membership(membership=self.membership, actor=self.owner)
        self.membership.refresh_from_db()
        self.assertFalse(self.membership.is_active)

        account_services.reactivate_membership(membership=self.membership, actor=self.owner)
        self.membership.refresh_from_db()
        self.assertTrue(self.membership.is_active)

    def test_role_change_does_not_duplicate_or_corrupt_membership(self):
        account_services.update_membership_role(membership=self.membership, new_role=self.role_b, actor=self.owner)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, self.role_b)
        self.assertEqual(Membership.objects.filter(user=self.staff_user, business=self.business).count(), 1)
