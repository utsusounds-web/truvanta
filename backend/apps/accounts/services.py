from django.core.exceptions import ValidationError

from apps.audit.services import log_action
from .models import User, Membership, Role


def set_duress_password(*, user, real_password_confirmation: str, new_duress_password: str):
    """Set/update the user's silent duress password. Requires the
    user's real current password as proof of identity (same
    confirmation pattern as any other credential change) — this
    endpoint itself is never reachable under coercion in the way the
    duress login is, since setting one up needs deliberate,
    unhurried access to Settings.
    """
    if not user.check_password(real_password_confirmation):
        raise ValidationError("Your current password is incorrect.")
    if len(new_duress_password) < 8:
        raise ValidationError("The duress password must be at least 8 characters.")
    if user.check_password(new_duress_password):
        raise ValidationError("The duress password can't be the same as your real password.")
    user.set_duress_password(new_duress_password)
    user.save(update_fields=["duress_password_hash"])


def handle_duress_login(*, user, request):
    """Called the moment a duress password is used to log in
    successfully — see accounts.views.SessionAwareTokenObtainPairView.
    Must never do anything that would be visible to whoever is
    physically present: no different response, no different UI
    signal, nothing. Everything here is purely backend-side: a
    critical, silent alert to every owner/admin across every business
    this user belongs to, and an audit trail entry business by
    business (AuditLog is inherently per-business, and a duress event
    is relevant to every business context this person could now act
    under).
    """
    from apps.notifications.services import notify

    memberships = Membership.objects.filter(user=user).select_related("business")
    ip = request.META.get("REMOTE_ADDR", "")
    for membership in memberships:
        business = membership.business
        log_action(
            business=business, actor=user, action="login",
            reason="Duress password used to log in — treat as a possible coercion/security incident.",
            ip_address=ip or None,
        )
        owner_admin_memberships = Membership.objects.filter(
            business=business, role__system_role__in=["owner", "admin"],
        ).exclude(user=user)
        if owner_admin_memberships.exists():
            notify(
                business=business, level="critical",
                title="Security alert — possible duress login",
                message=(
                    f"{user.get_full_name() or user.email} just logged in using their duress password. "
                    f"This usually means they are under pressure or being coerced. Consider discreetly "
                    f"checking on them or contacting authorities — do not confront the situation directly "
                    f"if there is any active threat."
                ),
                link_path="/staff-sessions",
            )


def invite_staff_member(*, business, branch, email, role, invited_by, password=None, first_name="", last_name=""):
    """Adds a Truvanta user to this business with a role.

    If `password` is given and no account exists for `email` yet, a
    brand-new account is created right here with that password — this
    is the "create a login for my new branch and hand it over myself"
    path, so a business owner never has to ask a branch manager to go
    register their own account first.

    If the account already exists, `password` is ignored and this
    just attaches the existing account to this business (the original
    behavior) — never silently resets someone's existing password.
    """
    try:
        user = User.objects.get(email__iexact=email)
        created = False
    except User.DoesNotExist:
        if not password:
            raise ValidationError(
                f"No Truvanta account found for {email}. Either give them a password to create "
                f"one now, or ask them to register first and try adding them again."
            )
        username_base = email.split("@")[0]
        username = username_base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{username_base}{suffix}"
        user = User.objects.create_user(
            email=email, username=username, password=password,
            first_name=first_name, last_name=last_name,
        )
        created = True

    if Membership.objects.filter(user=user, business=business, branch=branch).exists():
        raise ValidationError("This person is already a member of this business/branch.")

    membership = Membership.objects.create(user=user, business=business, branch=branch, role=role)
    log_action(
        business=business, actor=invited_by, action="permission_change", target=membership, branch=branch,
        new_value={"user": str(user.email), "role": role.name, "account_created": created},
        reason="Staff account created and added." if created else "Staff member added.",
    )
    return membership


def update_membership_role(*, membership: Membership, new_role: Role, actor):
    old_role = membership.role
    membership.role = new_role
    membership.save(update_fields=["role"])
    log_action(
        business=membership.business, actor=actor, action="permission_change", target=membership,
        previous_value={"role": old_role.name}, new_value={"role": new_role.name}, reason="Role changed.",
    )
    return membership


def deactivate_membership(*, membership: Membership, actor):
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    log_action(
        business=membership.business, actor=actor, action="permission_change", target=membership,
        previous_value={"is_active": True}, new_value={"is_active": False}, reason="Staff access revoked.",
    )
    return membership


def reactivate_membership(*, membership: Membership, actor):
    membership.is_active = True
    membership.save(update_fields=["is_active"])
    log_action(
        business=membership.business, actor=actor, action="permission_change", target=membership,
        previous_value={"is_active": False}, new_value={"is_active": True}, reason="Staff access restored.",
    )
    return membership
