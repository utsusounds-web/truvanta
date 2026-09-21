import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.crypto import EncryptedCharField


class User(AbstractUser):
    """Custom user. UUID pk so user IDs are never guessable/sequential
    across tenants, and email is the login identifier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=50, blank=True)
    profile_photo = models.ImageField(upload_to="user_profile_photos/", null=True, blank=True)

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = EncryptedCharField(
        max_length=255, blank=True, default="",
        help_text="TOTP secret, encrypted at rest. Blank until setup is confirmed (see accounts.views 2FA endpoints).",
    )

    # --- Silent duress password (differentiator feature) ---
    # A second password that, when used to log in, succeeds exactly
    # like the real one — same session, same UI, nothing visibly
    # different — while silently telling the business's owners/admins
    # something is wrong. This exists for the scenario the product
    # plan specifically calls out: someone being forced to open the
    # till under threat. Deliberately NOT a separate visible "duress
    # mode" toggle anywhere in the UI once set — its entire value is
    # that a coercer watching the screen sees nothing unusual happen.
    #
    # Stored as a normal Django password hash (via set_password-style
    # hashing, see set_duress_password/check_duress_password below),
    # then encrypted at rest on top of that — matching two_factor_secret's
    # belt-and-suspenders approach for the same reason: this is exactly
    # the kind of field where a database-only leak still shouldn't hand
    # an attacker anything directly usable.
    duress_password_hash = EncryptedCharField(
        max_length=255, blank=True, default="",
        help_text="Hashed duress password, encrypted at rest. Blank until the user sets one up in Security settings.",
    )

    def set_duress_password(self, raw_password: str):
        from django.contrib.auth.hashers import make_password
        self.duress_password_hash = make_password(raw_password)

    def check_duress_password(self, raw_password: str) -> bool:
        # NOTE: this is intentionally not constant-time relative to
        # "no duress password set" — a blank hash short-circuits
        # before any hashing happens, an account with one configured
        # always pays the hashing cost. That's a theoretical timing
        # side-channel (an attacker doing careful network timing
        # analysis across many failed logins could infer whether an
        # account has a duress password set up at all). Not defended
        # against here: this feature's actual threat model is physical
        # coercion, not a remote timing attack sophisticated enough to
        # measure single-digit-millisecond hashing differences over a
        # network, and adding artificial constant-time padding to
        # every login attempt for every user isn't worth that cost.
        from django.contrib.auth.hashers import check_password
        if not self.duress_password_hash or not raw_password:
            return False
        return check_password(raw_password, self.duress_password_hash)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Role(models.Model):
    """A named role scoped to a Business (owner can define custom roles
    beyond the defaults, e.g. 'Senior Cashier').

    system_role marks the built-in roles (owner/admin/cashier/inventory
    /accountant) that ship with every business and drive default
    permission sets; owners can still adjust granular permissions on
    the Membership level.
    """

    SYSTEM_ROLES = [
        ("owner", "Owner"),
        ("admin", "Admin / Manager"),
        ("cashier", "Sales Staff / Cashier"),
        ("inventory", "Inventory Staff"),
        ("accountant", "Accountant"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    system_role = models.CharField(max_length=20, choices=SYSTEM_ROLES, blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("business", "name")]

    def __str__(self):
        return f"{self.name} ({self.business.name})"


class Permission(models.Model):
    """A granular, sensitive action a role may or may not be allowed to
    perform. Deliberately separate from Django's built-in auth
    permissions because these map to real business-protection
    decisions (e.g. 'can view profit figures'), not just CRUD on a
    model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("role", "permission")]


class Membership(models.Model):
    """Links a User to a Business (and optionally a specific Branch)
    with a Role. This is the object that answers 'what can this user
    do, where'. A user with no Membership for a business has zero
    access to that business's data — this is what tenant isolation
    is enforced against.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="memberships")
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.CASCADE, related_name="memberships",
        null=True, blank=True, help_text="Leave blank for access to all branches of the business.",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    is_active = models.BooleanField(default=True)
    is_support_access = models.BooleanField(
        default=False,
        help_text="Marks this as a temporary platform-support login, created only while the "
                   "business's owner/admin has an active support-access grant open. Automatically "
                   "stops working the moment that grant expires or is revoked — see "
                   "get_active_membership().",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "business", "branch")]

    def __str__(self):
        return f"{self.user.email} @ {self.business.name} ({self.role.name})"

    def has_permission(self, code: str) -> bool:
        if not self.is_active:
            return False
        if self.role.system_role == "owner":
            return True
        if self._is_acting_owner_via_continuity():
            return True
        return RolePermission.objects.filter(role=self.role, permission__code=code).exists()

    def _is_acting_owner_via_continuity(self) -> bool:
        """True while Business Continuity Mode has elevated this
        person as the designated backup manager (see apps.continuity)
        — checked live against the current activation record rather
        than a stored flag on this row, so there's no way for a stale
        flag to leave someone elevated after the fact."""
        from apps.continuity.models import ContinuityActivation
        return ContinuityActivation.objects.filter(
            business=self.business, backup_manager=self.user, deactivated_at__isnull=True,
        ).exists()


class UserSession(models.Model):
    """One row per active login (i.e. per refresh-token chain), so a
    user can see every device they're logged in on and revoke any of
    them remotely — signing that device out immediately, not just
    hiding it locally. Tied to simplejwt's OutstandingToken: revoking
    means blacklisting that token, which the existing
    ROTATE_REFRESH_TOKENS/BLACKLIST_AFTER_ROTATION setup already
    enforces on every request.

    The row is repointed to the newest OutstandingToken each time the
    refresh token rotates (see accounts.views.refresh), so its id stays
    stable across a session's lifetime — that stable id is what the
    frontend keeps in localStorage to know "this is me" in the list.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    outstanding_token = models.OneToOneField(
        "token_blacklist.OutstandingToken", on_delete=models.CASCADE, related_name="user_session",
    )
    device_label = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"{self.user.email} — {self.device_label or 'unknown device'}"
