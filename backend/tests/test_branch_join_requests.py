from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, Membership
from apps.tenants.models import Branch, BranchJoinRequest
from tests.factories import make_user, make_business_with_owner


class BranchJoinRequestTests(TestCase):
    """A staff member with the signup code can request to join as a
    branch, but gets nothing until the owner/admin approves — and once
    approved, lands on a minimum-trust role, never owner/admin."""

    def setUp(self):
        self.owner = make_user()
        self.business, self.main_branch = make_business_with_owner(self.owner)

        self.applicant = make_user(email="applicant@example.com")
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.applicant_client = APIClient()
        self.applicant_client.force_authenticate(user=self.applicant)
        self.headers = {"HTTP_X_BUSINESS_ID": str(self.business.id)}

    def test_submitting_a_join_request_grants_no_access(self):
        r = self.applicant_client.post(
            "/api/tenants/branch-join-requests/submit/",
            {"signup_code": self.business.signup_code, "branch_name": "Wuse Branch"},
        )
        self.assertEqual(r.status_code, 201)
        self.assertFalse(Membership.objects.filter(user=self.applicant, business=self.business).exists())
        self.assertEqual(BranchJoinRequest.objects.get().status, "pending")

    def test_wrong_signup_code_is_rejected(self):
        r = self.applicant_client.post(
            "/api/tenants/branch-join-requests/submit/",
            {"signup_code": "WRONGCODE", "branch_name": "Wuse Branch"},
        )
        self.assertEqual(r.status_code, 400)

    def test_non_owner_cannot_approve(self):
        jr = BranchJoinRequest.objects.create(business=self.business, requested_by=self.applicant, branch_name="Wuse Branch")
        cashier_role = Role.objects.create(business=self.business, name="Cashier", system_role="cashier")
        Membership.objects.create(user=self.applicant, business=self.business, branch=self.main_branch, role=cashier_role)
        cashier_client = APIClient()
        cashier_client.force_authenticate(user=self.applicant)
        r = cashier_client.post(f"/api/tenants/branch-join-requests/{jr.id}/approve/", **self.headers)
        self.assertEqual(r.status_code, 403)

    def test_owner_approval_creates_branch_and_cashier_only_membership(self):
        jr = BranchJoinRequest.objects.create(business=self.business, requested_by=self.applicant, branch_name="Wuse Branch")
        r = self.owner_client.post(f"/api/tenants/branch-join-requests/{jr.id}/approve/", **self.headers)
        self.assertEqual(r.status_code, 200)

        jr.refresh_from_db()
        self.assertEqual(jr.status, "approved")
        self.assertIsNotNone(jr.created_branch)
        self.assertEqual(jr.created_branch.name, "Wuse Branch")

        membership = Membership.objects.get(user=self.applicant, business=self.business)
        self.assertEqual(membership.branch_id, jr.created_branch_id)
        self.assertEqual(membership.role.system_role, "cashier")
        self.assertNotIn(membership.role.system_role, ["owner", "admin"])

    def test_rejecting_grants_no_branch_or_membership(self):
        jr = BranchJoinRequest.objects.create(business=self.business, requested_by=self.applicant, branch_name="Wuse Branch")
        r = self.owner_client.post(f"/api/tenants/branch-join-requests/{jr.id}/reject/", **self.headers)
        self.assertEqual(r.status_code, 200)
        jr.refresh_from_db()
        self.assertEqual(jr.status, "rejected")
        self.assertFalse(Membership.objects.filter(user=self.applicant, business=self.business).exists())
        self.assertFalse(Branch.objects.filter(business=self.business, name="Wuse Branch").exists())

    def test_duplicate_branch_name_is_rejected_cleanly(self):
        jr = BranchJoinRequest.objects.create(business=self.business, requested_by=self.applicant, branch_name=self.main_branch.name)
        r = self.owner_client.post(f"/api/tenants/branch-join-requests/{jr.id}/approve/", **self.headers)
        self.assertEqual(r.status_code, 400)
        jr.refresh_from_db()
        self.assertEqual(jr.status, "pending")  # unchanged — still approvable once renamed
