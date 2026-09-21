from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.accounts.models import Membership


def _excluding_expired_support_access(queryset):
    """A support-access Membership (see AdminSupportLoginView) is only
    ever valid while its business's support_access_expires_at is set
    and in the future — checked live on every request, the same
    philosophy as Business Continuity's backup-manager elevation,
    rather than trusting a stored flag that could go stale after the
    owner revokes or the window lapses."""
    now = timezone.now()
    return [
        m for m in queryset
        if not m.is_support_access or (m.business.support_access_expires_at and m.business.support_access_expires_at > now)
    ]


def get_active_membership(user, business_id):
    """Return the user's primary active Membership for a business, or
    None. This is the single choke point tenant isolation is enforced
    through — a user with no active membership has zero access.

    A user can hold several Memberships for the same business (one
    per branch they've been given access to, per the unique_together
    on Membership). For role/permission checks we need one canonical
    membership, so we prefer — in order — an owner-role membership,
    then any membership with no branch restriction (full access),
    then whichever membership exists first."""
    if not business_id:
        return None
    memberships = _excluding_expired_support_access(
        Membership.objects.filter(user=user, business_id=business_id, is_active=True).select_related("role", "business")
    )
    if not memberships:
        return None
    for m in memberships:
        if m.role.system_role == "owner":
            return m
    for m in memberships:
        if m.branch_id is None:
            return m
    return memberships[0]


def get_accessible_branch_ids(user, business_id):
    """Returns None if the user can see every branch of the business
    (owner/admin, or holds any membership with no branch restriction),
    otherwise a set of the specific branch ids they're allowed to
    see. A mini branch is automatically included whenever its main
    branch is accessible, since it's controlled by that main branch."""
    if not business_id:
        return set()
    memberships = _excluding_expired_support_access(
        Membership.objects.filter(user=user, business_id=business_id, is_active=True).select_related("role", "business")
    )
    if not memberships:
        return set()
    if any(m.role.system_role in ("owner", "admin") or m.branch_id is None for m in memberships):
        return None
    from apps.tenants.models import Branch

    branch_ids = {m.branch_id for m in memberships}
    if hasattr(Branch, "parent_branch"):
        branch_ids |= set(Branch.objects.filter(parent_branch_id__in=branch_ids).values_list("id", flat=True))
    return branch_ids


class IsBusinessMember(BasePermission):
    """Requires the request to carry a resolvable business (via
    X-Business-ID header or ?business= param) and the user to have an
    active Membership in it. ViewSets should further filter querysets
    by this same business to prevent cross-tenant reads."""

    message = "You do not have access to this business."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        business_id = request.headers.get("X-Business-ID") or request.query_params.get("business")
        membership = get_active_membership(request.user, business_id)
        if membership is None:
            return False
        request.membership = membership
        request.business_id = business_id
        request.accessible_branch_ids = get_accessible_branch_ids(request.user, business_id)
        return True


class HasBusinessPermission(IsBusinessMember):
    """Subclass and set `required_permission_code` to also require a
    specific granular Permission (e.g. 'view_profit') beyond plain
    membership."""

    required_permission_code = None

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if self.required_permission_code and not request.membership.has_permission(self.required_permission_code):
            return False
        return True


class IsOwnerOrAdmin(IsBusinessMember):
    """Requires the resolved membership to actually hold the owner or
    admin role — for things no granular permission code covers because
    they sit above ordinary staff permissions entirely (security/audit
    history, business-level settings, approving new branches). Also
    true for a business's designated Business Continuity backup
    manager while continuity mode is actively elevated for them (see
    Membership._is_acting_owner_via_continuity) — the whole point of
    that feature is equal footing with an owner for its duration.

    Deliberately does NOT treat a branch-unrestricted membership
    (branch_id is None) as owner/admin — that field only means "can
    see every branch's data" (see get_accessible_branch_ids), which is
    a data-visibility scope, not an administrative privilege. A staff
    member on a narrow custom role who happens to work across branches
    should not thereby gain owner-level actions."""

    message = "Only an owner or admin can do this."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        m = request.membership
        # Deliberately NOT `or m.branch_id is None` — that field means
        # "this membership can see every branch's data" (a visibility
        # scope, see get_accessible_branch_ids), which is a completely
        # different thing from being an owner/admin. Conflating the two
        # used to let any branch-unrestricted staff member (e.g. a
        # multi-branch bookkeeper on a narrow custom role) silently
        # gain owner-level actions — approving new branches, seeing the
        # signup code, security/audit settings — despite never being
        # granted that role.
        return m.role.system_role in ("owner", "admin") or m._is_acting_owner_via_continuity()
