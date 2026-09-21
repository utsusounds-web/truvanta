from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import generics, permissions, viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, Membership
from apps.audit.services import log_action
from apps.billing.permissions import IsPlatformAdmin
from apps.billing.services import business_has_feature
from apps.core.permissions import IsBusinessMember, IsOwnerOrAdmin
from apps.core.viewsets import TenantScopedModelViewSet
from rest_framework.exceptions import PermissionDenied
from .models import Business, Branch, BranchJoinRequest
from .serializers import BusinessSerializer, BranchSerializer, BranchJoinRequestSerializer


def _require_additional_branch_allowed(business_id):
    """A business's first branch (created automatically at signup) is
    always free — this only applies from the second branch onward,
    which is the actual 'multi_branch' paid feature. Checked inline
    (like reports' CSV-export gate) rather than as a view-level
    permission, since branch #1 must still go through this same
    creation code path."""
    if Branch.objects.filter(business_id=business_id).exists() and not business_has_feature(business_id, "multi_branch"):
        raise PermissionDenied("Adding more than one branch isn't included in your current plan.")


DEFAULT_UNITS = [
    ("Piece", "pc"),
    ("Kilogram", "kg"),
    ("Litre", "L"),
    ("Carton", "ctn"),
    ("Pack", "pack"),
]

DEFAULT_EXPENSE_CATEGORIES = ["Rent", "Utilities", "Transport", "Salaries", "Miscellaneous"]


def _seed_default_units(business):
    """A brand-new business has no units of measure yet, and the
    product form's unit field is a dropdown (not free text) — with
    nothing to select, the owner can't actually finish adding their
    first product until they notice the separate 'add a unit' control.
    Seeding a few common ones removes that dead end entirely; they're
    ordinary UnitOfMeasure rows the owner can rename or add to freely.
    """
    from apps.products.models import UnitOfMeasure
    UnitOfMeasure.objects.bulk_create([
        UnitOfMeasure(business=business, name=name, abbreviation=abbr) for name, abbr in DEFAULT_UNITS
    ])


def _seed_default_expense_categories(business):
    """Same dead-end as units, same fix: the expense form's category
    field is also a dropdown with an easy-to-miss 'add category'
    control next to it — seed a few common ones so recording the
    first expense doesn't require noticing that first.
    """
    from apps.expenses.models import ExpenseCategory
    ExpenseCategory.objects.bulk_create([
        ExpenseCategory(business=business, name=name) for name in DEFAULT_EXPENSE_CATEGORIES
    ])


TRIAL_LENGTH_DAYS = 30


def _start_free_trial(business):
    """Every new business gets a genuine, automatic 30-day free trial
    with full feature access — not a watered-down preview, and not
    something an owner has to notice a button for and turn on
    themselves. This is deliberately unconditional: it's part of
    signing up, not a separate step that could be skipped.

    Core operation (sales, expenses, customers, simple stock, basic
    reports) was never feature-gated in the first place and keeps
    working forever regardless of trial or subscription status — see
    business_has_feature's docstring. The trial's only job is to let
    a new business see what the paid tiers add before the 30 days are
    up, so the decision to subscribe is an informed one.
    """
    from apps.billing.models import Subscription

    Subscription.objects.get_or_create(
        business=business,
        defaults={"status": "trialing", "current_period_end": timezone.now() + timedelta(days=TRIAL_LENGTH_DAYS)},
    )


def _unique_slug(name: str) -> str:
    base = slugify(name) or "business"
    slug = base
    n = 1
    while Business.objects.filter(slug=slug).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug


def _unique_signup_code() -> str:
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not Business.objects.filter(signup_code=code).exists():
            return code


class BusinessCreateView(generics.CreateAPIView):
    """Onboarding entry point (spec section 32): create the Business
    (with branding fields — logo, name, address, phone) and, in the
    same transaction, an Owner Role + Membership for the creating
    user, plus a default 'Main Branch'. There's no membership yet at
    this point, so this intentionally bypasses IsBusinessMember.
    """
    serializer_class = BusinessSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            business = serializer.save(owner=request.user, slug=_unique_slug(serializer.validated_data["name"]), signup_code=_unique_signup_code())
            owner_role = Role.objects.create(business=business, name="Owner", system_role="owner")
            Membership.objects.create(user=request.user, business=business, role=owner_role)
            branch = Branch.objects.create(business=business, name="Main Branch")
            _seed_default_units(business)
            _seed_default_expense_categories(business)
            _start_free_trial(business)
            log_action(
                business=business, actor=request.user, action="create", target=business,
                new_value={"name": business.name}, reason="Business created during onboarding.",
            )
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"business": BusinessSerializer(business, context={"request": request}).data,
             "default_branch": BranchSerializer(branch, context={"request": request}).data},
            status=201, headers=headers,
        )


class BusinessDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve/update a single business's profile & branding. Update
    is how the owner changes the logo/name/receipt footer etc. that
    then flows into every generated document via Business.branding_context.
    """
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        # Any active member can view the business profile (the logo/name
        # need to render for everyone using the app), but changing the
        # logo or any other branding/settings field is owner/admin only —
        # matches what the Settings page UI already assumes.
        if self.request.method in ("PUT", "PATCH"):
            return [IsOwnerOrAdmin()]
        return [IsBusinessMember()]

    def get_object(self):
        obj = super().get_object()
        return obj

    def perform_update(self, serializer):
        # Turning Away Mode ON is the paid action here — turning it
        # OFF, or updating unrelated fields, always goes through
        # regardless of plan. Checked against validated_data (the
        # incoming change) rather than the saved instance, so this
        # can't be bypassed by sending the same field back unchanged.
        turning_away_mode_on = serializer.validated_data.get("away_mode_enabled") is True
        if turning_away_mode_on and not business_has_feature(self.request.business_id, "away_mode"):
            raise PermissionDenied("Owner Away Mode isn't included in your current plan.")
        previous = BusinessSerializer(serializer.instance, context={"request": self.request}).data
        business = serializer.save()
        log_action(
            business=business, actor=self.request.user, action="update", target=business,
            previous_value=previous, new_value=BusinessSerializer(business, context={"request": self.request}).data,
            reason="Business profile/branding updated.",
        )


class BranchViewSet(TenantScopedModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        # Any accessible-branch member can view branches (POS needs to
        # know which branch it's operating as), but creating a branch,
        # renaming one, or changing its logo/address override is
        # owner/admin only — a cashier should never be able to touch
        # this, let alone override the business's branding.
        if self.request.method not in permissions.SAFE_METHODS:
            return [IsOwnerOrAdmin()]
        return [IsBusinessMember()]

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is None:
            return qs
        return qs.filter(id__in=accessible)

    def perform_create(self, serializer):
        # Same fix as Product/Customer: multipart form data with no
        # is_active key is treated by DRF as an unchecked checkbox
        # (False), not "use the model default".
        _require_additional_branch_allowed(self.request.business_id)
        extra = {}
        if "is_active" not in self.request.data:
            extra["is_active"] = True
        serializer.save(business_id=self.request.business_id, **extra)


def _get_or_create_cashier_role(business: Business) -> Role:
    """The minimum-trust role a newly-approved branch join request gets
    put on. Reuses whatever role is already marked system_role='cashier'
    for this business if one exists; otherwise creates one — falling
    back to a disambiguated name if a custom role is already using
    the plain "Cashier" name without being marked as the system role.
    """
    existing = Role.objects.filter(business=business, system_role="cashier").first()
    if existing:
        return existing
    name = "Cashier"
    if Role.objects.filter(business=business, name=name).exists():
        name = "Cashier (branch default)"
    return Role.objects.create(business=business, name=name, system_role="cashier")


class RegenerateSignupCodeView(APIView):
    """Owner/admin: invalidate the current signup code and issue a new
    one. Anyone who had the old code (e.g. it leaked, or an ex-staff
    member kept it) can no longer submit a join request with it."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request, business_id):
        business = generics.get_object_or_404(Business, id=business_id)
        old_code = business.signup_code
        business.signup_code = _unique_signup_code()
        business.save(update_fields=["signup_code"])
        log_action(
            business=business, actor=request.user, action="update", target=business,
            previous_value={"signup_code": old_code}, new_value={"signup_code": business.signup_code},
            reason="Branch signup code regenerated.",
        )
        return Response(BusinessSerializer(business, context={"request": request}).data)


class BranchJoinRequestCreateView(generics.CreateAPIView):
    """A staff member with a business's signup code, asking to register
    their own location as a branch. Deliberately bypasses IsBusinessMember
    — like BusinessCreateView, the whole point is the requester has no
    membership yet. They get nothing until an owner/admin approves."""
    serializer_class = BranchJoinRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        signup_code = (request.data.get("signup_code") or "").strip().upper()
        branch_name = (request.data.get("branch_name") or "").strip()
        if not signup_code or not branch_name:
            return Response({"detail": "signup_code and branch_name are required."}, status=400)
        business = Business.objects.filter(signup_code=signup_code, is_active=True).first()
        if not business:
            return Response({"detail": "That signup code isn't recognized. Double-check it with your business owner."}, status=400)
        if Membership.objects.filter(user=request.user, business=business, is_active=True).exists():
            return Response({"detail": "You're already a member of this business."}, status=400)
        if BranchJoinRequest.objects.filter(business=business, requested_by=request.user, status="pending").exists():
            return Response({"detail": "You already have a pending join request for this business."}, status=400)
        join_request = BranchJoinRequest.objects.create(
            business=business, requested_by=request.user, branch_name=branch_name,
        )
        return Response(
            BranchJoinRequestSerializer(join_request, context={"request": request}).data, status=201,
        )


class BranchJoinRequestListView(generics.ListAPIView):
    """Owner/admin: pending (and past) join requests for this business."""
    serializer_class = BranchJoinRequestSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return BranchJoinRequest.objects.filter(business_id=self.request.business_id).select_related("requested_by", "reviewed_by")


class BranchJoinRequestApproveView(APIView):
    """Owner/admin approving a join request: creates the Branch and a
    minimum-trust (Cashier) Membership for the requester — never
    owner/admin, and never with access to other branches. The owner
    can upgrade their role/access afterwards from Staff & Roles like
    any other staff member."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request, pk):
        join_request = generics.get_object_or_404(
            BranchJoinRequest, pk=pk, business_id=request.business_id, status="pending",
        )
        if Branch.objects.filter(business=join_request.business, name=join_request.branch_name).exists():
            return Response(
                {"detail": f"A branch named '{join_request.branch_name}' already exists. "
                           f"Ask the requester to resubmit with a different name."},
                status=400,
            )
        _require_additional_branch_allowed(join_request.business_id)
        with transaction.atomic():
            branch = Branch.objects.create(business=join_request.business, name=join_request.branch_name)
            cashier_role = _get_or_create_cashier_role(join_request.business)
            Membership.objects.create(
                user=join_request.requested_by, business=join_request.business,
                branch=branch, role=cashier_role,
            )
            join_request.status = "approved"
            join_request.reviewed_by = request.user
            join_request.reviewed_at = timezone.now()
            join_request.created_branch = branch
            join_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "created_branch"])
            log_action(
                business=join_request.business, actor=request.user, action="create", target=branch,
                new_value={"branch_name": branch.name, "approved_for": join_request.requested_by.email},
                reason="Branch join request approved.",
            )
        return Response(BranchJoinRequestSerializer(join_request, context={"request": request}).data)


class BranchJoinRequestRejectView(APIView):
    """Owner/admin rejecting a join request. No branch, no membership —
    the requester's account stays exactly as it was, with zero access."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request, pk):
        join_request = generics.get_object_or_404(
            BranchJoinRequest, pk=pk, business_id=request.business_id, status="pending",
        )
        join_request.status = "rejected"
        join_request.reviewed_by = request.user
        join_request.reviewed_at = timezone.now()
        join_request.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        log_action(
            business=join_request.business, actor=request.user, action="update", target=join_request.business,
            reason=f"Branch join request from {join_request.requested_by.email} rejected.",
        )
        return Response(BranchJoinRequestSerializer(join_request, context={"request": request}).data)


class BusinessSupportAccessGrantView(APIView):
    """Owner/admin only: opens a time-limited window during which
    Truvanta platform staff can log into this business to help with
    support. Nothing happens automatically — a staff member still has
    to actively use AdminSupportLoginView while this window is open,
    and every such login is logged to this business's own Activity Log
    so it's never invisible to the owner."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request):
        hours = int(request.data.get("hours", 24))
        hours = max(1, min(hours, 24 * 7))  # cap at 7 days
        business = generics.get_object_or_404(Business, id=request.business_id)
        business.support_access_expires_at = timezone.now() + timedelta(hours=hours)
        business.save(update_fields=["support_access_expires_at"])
        log_action(
            business=business, actor=request.user, action="update", target=business,
            reason=f"Granted platform support access for {hours} hour(s).",
        )
        return Response({"support_access_expires_at": business.support_access_expires_at})


class BusinessSupportAccessRevokeView(APIView):
    """Owner/admin only: closes the window immediately, and also
    removes any support-access membership that's already been created
    for this business — not just future logins, this ends any support
    session in progress right now too."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request):
        business = generics.get_object_or_404(Business, id=request.business_id)
        business.support_access_expires_at = None
        business.save(update_fields=["support_access_expires_at"])
        removed = Membership.objects.filter(business=business, is_support_access=True)
        removed_count = removed.count()
        removed.delete()
        log_action(
            business=business, actor=request.user, action="update", target=business,
            reason=f"Revoked platform support access ({removed_count} active support session(s) ended).",
        )
        return Response({"support_access_expires_at": None})


class AdminSupportLoginView(APIView):
    """Platform staff only. Only works while the target business's
    owner/admin has an open support-access window (see
    BusinessSupportAccessGrantView) — there is deliberately no way for
    staff to grant this to themselves. Gives the staff member a real,
    clearly-labelled Membership (visible to the owner on the Staff
    page like any other) with full owner-equivalent access, which
    silently stops working the moment the window closes — see
    get_active_membership() in apps.core.permissions.
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        business_id = request.data.get("business_id")
        business = generics.get_object_or_404(Business, id=business_id)
        if not business.support_access_expires_at or business.support_access_expires_at <= timezone.now():
            return Response(
                {"detail": "This business hasn't granted platform support access, or the window has expired."},
                status=403,
            )
        support_role, _ = Role.objects.get_or_create(
            business=business, system_role="owner", name="Platform Support (temporary)",
        )
        membership, created = Membership.objects.get_or_create(
            user=request.user, business=business, branch=None,
            defaults={"role": support_role, "is_support_access": True},
        )
        if not created and not membership.is_support_access:
            # This staff member already has a real, pre-existing
            # membership on this business (they're a genuine employee/
            # owner of it) — never let a support-login click silently
            # overwrite that with the temporary support role.
            return Response(
                {"detail": "You already have your own membership on this business — just switch to it normally instead of using support access."},
                status=400,
            )
        if not created:
            membership.role = support_role
            membership.is_support_access = True
            membership.is_active = True
            membership.save(update_fields=["role", "is_support_access", "is_active"])
        log_action(
            business=business, actor=request.user, action="update", target=business,
            reason=f"Platform support ({request.user.email}) logged in with the business's own granted access.",
        )
        return Response({"business_id": str(business.id), "business_name": business.name})
