from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import viewsets

from apps.audit.services import log_action
from apps.core.permissions import IsBusinessMember, HasBusinessPermission, IsOwnerOrAdmin
from apps.billing.permissions import IsPlatformAdmin
from apps.core.viewsets import TenantScopedModelViewSet
from .models import Membership, Role, Permission, RolePermission, User
from .serializers import (
    RegisterSerializer, UserSerializer, MembershipSerializer,
    RoleSerializer, PermissionSerializer, StaffInviteSerializer,
)
from . import services


class RequireManageStaff(HasBusinessPermission):
    required_permission_code = "manage_staff"


class RegisterView(generics.CreateAPIView):
    """Public sign-up. Creating a Business (and the owner Membership)
    happens separately via tenants.views.BusinessCreateView once the
    account exists, per the onboarding flow in the spec."""
    queryset = None
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"
    throttle_classes = [ScopedRateThrottle]

    def perform_create(self, serializer):
        user = serializer.save()
        log_action(business=None, actor=user, action="create", reason="User account registered.")


class MeView(APIView):
    """Returns the authenticated user plus every business they belong
    to, so the frontend can drive a business switcher. Also accepts
    PATCH to update the user's own profile (name, phone, photo)."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        memberships = Membership.objects.filter(user=request.user, is_active=True).select_related(
            "business", "branch", "role"
        )
        return Response({
            "user": UserSerializer(request.user, context={"request": request}).data,
            "memberships": MembershipSerializer(memberships, many=True).data,
        })

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PermissionListView(generics.ListAPIView):
    """Full catalog of granular permission codes a role can be given."""
    queryset = Permission.objects.all().order_by("category", "code")
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoleViewSet(TenantScopedModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    def get_permissions(self):
        # Reading roles (e.g. populating the "assign role" dropdown
        # on the Staff page) is fine for any business member. Creating,
        # editing, deleting a role, or changing what it can do is
        # exactly "manage staff, roles, and permissions" — restricted.
        if self.action in ("list", "retrieve"):
            return [IsBusinessMember()]
        return [RequireManageStaff()]

    @action(detail=True, methods=["post"], url_path="set-permissions")
    def set_permissions(self, request, pk=None):
        """Replace this role's granular permissions with the given
        list of codes. Owner-role permissions are implicit (see
        Membership.has_permission) and not affected by this."""
        role = self.get_object()
        codes = request.data.get("permission_codes", [])
        permissions_qs = Permission.objects.filter(code__in=codes)
        RolePermission.objects.filter(role=role).delete()
        RolePermission.objects.bulk_create([RolePermission(role=role, permission=p) for p in permissions_qs])
        log_action(
            business=role.business, actor=request.user, action="permission_change", target=role,
            new_value={"permission_codes": list(codes)}, reason="Role permissions updated.",
        )
        return Response(RoleSerializer(role).data)


class MembershipViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]  # no direct create — use /staff/invite/
    queryset = Membership.objects.select_related("user", "role", "branch")
    serializer_class = MembershipSerializer
    filterset_fields = ["branch", "role", "is_active"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsBusinessMember()]
        return [RequireManageStaff()]

    def create(self, request, *args, **kwargs):
        raise DRFValidationError("Add staff via POST /api/staff/invite/ instead.")

    def perform_update(self, serializer):
        instance = serializer.instance
        data = self.request.data
        handled = False

        new_role_id = data.get("role")
        if new_role_id and str(instance.role_id) != str(new_role_id):
            new_role = Role.objects.get(pk=new_role_id, business_id=self.request.business_id)
            services.update_membership_role(membership=instance, new_role=new_role, actor=self.request.user)
            instance.refresh_from_db()
            handled = True

        if "is_active" in data:
            new_active = data["is_active"] in (True, "true", "True", "1", 1)
            if new_active != instance.is_active:
                if new_active:
                    services.reactivate_membership(membership=instance, actor=self.request.user)
                else:
                    services.deactivate_membership(membership=instance, actor=self.request.user)
            handled = True

        # Any other field (e.g. branch reassignment) that wasn't already
        # persisted via an audit-logged service call above.
        remaining_fields = set(serializer.validated_data.keys()) - {"role", "is_active"}
        if remaining_fields or not handled:
            serializer.save()


class StaffInviteView(APIView):
    """Sends an invite email — scoped separately from the blanket
    300/min user rate since that's loose enough to email-bomb an
    inbox by repeatedly inviting the same address."""
    permission_classes = [RequireManageStaff]
    throttle_scope = "staff_invite"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        s = StaffInviteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.tenants.models import Business, Branch
        business = Business.objects.get(pk=request.business_id)
        role = Role.objects.get(pk=s.validated_data["role"], business=business)
        branch = None
        if s.validated_data.get("branch"):
            branch = Branch.objects.get(pk=s.validated_data["branch"], business=business)
        try:
            membership = services.invite_staff_member(
                business=business, branch=branch, email=s.validated_data["email"],
                role=role, invited_by=request.user,
                password=s.validated_data.get("password") or None,
                first_name=s.validated_data.get("first_name", ""),
                last_name=s.validated_data.get("last_name", ""),
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(MembershipSerializer(membership).data, status=201)


class PasswordResetRequestView(APIView):
    """Public — request a reset link by email. Always returns 200
    regardless of whether the email exists, so a caller can't use
    this to discover which addresses have accounts."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        email = request.data.get("email", "")
        if email:
            from .password_reset import request_password_reset
            request_password_reset(email)
        return Response({"detail": "If that email has an account, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    """Public — complete a reset given the uid/token from the emailed link."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        from .password_reset import confirm_password_reset
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")
        if not (uid and token and new_password):
            return Response({"detail": "uid, token, and new_password are all required."}, status=400)
        success, error = confirm_password_reset(uid, token, new_password)
        if not success:
            return Response({"detail": error}, status=400)
        return Response({"detail": "Password updated. You can sign in now."})


# --- Sessions / device management -------------------------------------
# See models.UserSession for the design. Both token views below are
# thin wrappers around simplejwt's own views — all the actual
# token issuing/rotation/validation logic is still simplejwt's; we
# only hook in before/after to keep a UserSession row in sync.

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # noqa: E402
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: E402
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken  # noqa: E402

import base64
import io

import pyotp
import qrcode
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from .device import parse_device_label, get_client_ip  # noqa: E402
from .models import UserSession  # noqa: E402
from .serializers import UserSessionSerializer, BusinessStaffSessionSerializer  # noqa: E402


import logging

logger = logging.getLogger(__name__)


def _record_session(request, refresh_str: str) -> str | None:
    """Create the UserSession row for a freshly issued refresh token.
    Returns its id (frontend stores this to identify 'this device')."""
    try:
        token = RefreshToken(refresh_str)
        outstanding = OutstandingToken.objects.get(jti=token["jti"])
    except Exception:
        logger.warning("Could not record login session — the device won't appear in Active Sessions.", exc_info=True)
        return None
    session = UserSession.objects.create(
        user_id=outstanding.user_id,
        outstanding_token=outstanding,
        device_label=parse_device_label(request.META.get("HTTP_USER_AGENT", "")),
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )
    return str(session.id)


def _mark_real_login(user) -> None:
    """Django's built-in last_login tracking only fires through the
    session-auth login() call, which this JWT-based flow never uses —
    so nothing was ever updating it. Fixed here rather than left
    silently broken: Business Continuity Mode (apps.continuity) reads
    this field to know how long it's been since an owner was last
    active, and would never have worked at all without it.

    Deliberately NOT called from the duress-login path (see
    _try_duress_login) — a duress login should keep continuity mode's
    inactivity clock ticking rather than resetting it, so a business
    still eventually gets that protection even through repeated
    coerced logins, rather than an attacker's forced access
    perpetually looking like the owner is fine.
    """
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])


def _check_continuity_for_user(user) -> None:
    """Business Continuity Mode only needs re-evaluating at the
    moments someone's login status could plausibly change it — a
    real login, not every authenticated request — so it's hooked in
    here rather than in middleware. Failure here should never break
    login itself."""
    from apps.accounts.models import Membership
    from apps.continuity.services import check_and_apply_continuity
    try:
        businesses = {m.business for m in Membership.objects.filter(user=user, is_active=True).select_related("business")}
        for business in businesses:
            check_and_apply_continuity(business=business)
    except Exception:
        logger.warning("Continuity check failed during login — login itself still succeeded.", exc_info=True)


def _repoint_session(request, old_refresh_str: str, new_refresh_str: str) -> None:
    """On rotation, move the existing UserSession onto the new
    OutstandingToken instead of creating a new row — this is what
    keeps 'this device' stable across a session's whole lifetime."""
    try:
        old_jti = RefreshToken(old_refresh_str)["jti"]
        new_token = RefreshToken(new_refresh_str)
        new_outstanding = OutstandingToken.objects.get(jti=new_token["jti"])
    except Exception:
        logger.warning("Could not repoint session on token refresh — device may vanish from Active Sessions.", exc_info=True)
        return
    session = UserSession.objects.filter(outstanding_token__jti=old_jti).first()
    if session:
        session.outstanding_token = new_outstanding
        session.ip_address = get_client_ip(request) or session.ip_address
        session.save(update_fields=["outstanding_token", "last_seen_at", "ip_address"])


class SessionAwareTokenObtainPairView(TokenObtainPairView):
    """Login. Identical response shape to stock simplejwt, plus a
    `session_id` field the frontend keeps to identify this device in
    the sessions list.

    If the account has 2FA enabled, credentials alone are NOT enough:
    real tokens are withheld and a short-lived `pre_auth_token` is
    returned instead — the frontend must then call
    Verify2FALoginView with a TOTP code to actually get signed in.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Real credentials failed — before falling through to
            # simplejwt's normal error response, silently check
            # whether this was actually a duress-password login. This
            # must produce an IDENTICAL success response to a normal
            # login on match — see services.handle_duress_login's
            # docstring for why nothing here can ever look different.
            duress_response = self._try_duress_login(request)
            if duress_response is not None:
                return duress_response
            # Preserve stock simplejwt's exact error response for bad
            # credentials — only the success path changes here.
            return super().post(request, *args, **kwargs)

        user = serializer.user
        if user.two_factor_enabled:
            pre_auth_token = TimestampSigner().sign(str(user.id))
            return Response({"requires_2fa": True, "pre_auth_token": pre_auth_token})

        response = Response(serializer.validated_data, status=200)
        if response.data.get("refresh"):
            response.data["session_id"] = _record_session(request, response.data["refresh"])
        _mark_real_login(user)
        _check_continuity_for_user(user)
        return response

    def _try_duress_login(self, request):
        """Returns a normal-looking successful login response if the
        submitted password matches the user's duress password,
        otherwise None (falls through to the real failure). 2FA is
        deliberately skipped even if enabled — demanding a second
        factor from someone who may be under physical threat would be
        actively dangerous, and the entire point of this feature is
        that it works exactly as smoothly as a normal login."""
        from .models import User
        from .services import handle_duress_login

        email = request.data.get("email") or request.data.get(User.USERNAME_FIELD)
        password = request.data.get("password", "")
        if not email or not password:
            return None
        user = User.objects.filter(email__iexact=email).first()
        if not user or not user.is_active or not user.check_duress_password(password):
            return None

        handle_duress_login(user=user, request=request)

        refresh = RefreshToken.for_user(user)
        response = Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)
        response.data["session_id"] = _record_session(request, response.data["refresh"])
        return response


class GoogleLoginView(APIView):
    """Sign in via a Google ID token from the frontend's Google
    Identity Services button — creating the account on first sign-in
    if none exists yet for that email. Identical response shape to
    the normal login endpoint, including still honoring 2FA if the
    account has it enabled: that's an account-level protection,
    independent of which method supplied the first factor.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        id_token = request.data.get("id_token")
        if not id_token:
            raise DRFValidationError({"id_token": "Required."})

        from apps.notifications.models import PlatformSettings
        client_id = PlatformSettings.load().google_oauth_client_id
        if not client_id:
            return Response({"detail": "Google sign-in isn't configured for this platform yet."}, status=503)

        import requests
        try:
            google_response = requests.get(
                "https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=8,
            )
        except requests.RequestException:
            return Response({"detail": "Couldn't reach Google to verify that sign-in. Try again."}, status=502)

        if google_response.status_code != 200:
            return Response({"detail": "That Google sign-in couldn't be verified. Try again."}, status=401)

        payload = google_response.json()
        # aud must match OUR client ID specifically — otherwise a valid
        # Google token issued for a completely different app could be
        # replayed here to sign in as that same person on Truvanta.
        if payload.get("aud") != client_id:
            return Response({"detail": "That Google sign-in wasn't issued for this app."}, status=401)
        if str(payload.get("email_verified")).lower() != "true":
            return Response({"detail": "Your Google account's email isn't verified."}, status=401)

        email = payload.get("email")
        if not email:
            return Response({"detail": "Google didn't provide an email for this account."}, status=401)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            user = self._create_user_from_google(email, payload)
        elif not user.is_active:
            return Response({"detail": "This account has been deactivated."}, status=403)

        if user.two_factor_enabled:
            pre_auth_token = TimestampSigner().sign(str(user.id))
            return Response({"requires_2fa": True, "pre_auth_token": pre_auth_token})

        refresh = RefreshToken.for_user(user)
        response = Response({"refresh": str(refresh), "access": str(refresh.access_token)}, status=200)
        response.data["session_id"] = _record_session(request, response.data["refresh"])
        _mark_real_login(user)
        _check_continuity_for_user(user)
        return response

    def _create_user_from_google(self, email, payload):
        base_username = email.split("@")[0]
        username = base_username
        n = 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base_username}{n}"
        user = User(
            email=email, username=username,
            first_name=payload.get("given_name", "") or "",
            last_name=payload.get("family_name", "") or "",
        )
        # No password was ever set — this account can only ever sign
        # in via Google, matching Django's own recommended pattern for
        # externally-authenticated accounts (set_unusable_password is
        # not the same as a blank password; it can never match any
        # submitted password at all).
        user.set_unusable_password()
        # Same "first account on a fresh install becomes platform
        # admin" rule as RegisterSerializer.create — kept consistent
        # so it doesn't matter which sign-in path someone's first
        # account happens to go through.
        if not User.objects.exists():
            user.is_staff = True
        user.save()
        return user


class SessionAwareTokenRefreshView(TokenRefreshView):
    """Token refresh. Repoints the existing UserSession onto the newly
    rotated refresh token instead of losing track of it."""

    def post(self, request, *args, **kwargs):
        old_refresh = request.data.get("refresh", "")
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200 and response.data.get("refresh") and old_refresh:
            _repoint_session(request, old_refresh, response.data["refresh"])
        return response


class LogoutView(APIView):
    """Explicit logout — blacklists the refresh token server-side so it
    can't be used again, and removes the UserSession row. Without this,
    'logging out' only ever cleared localStorage; the refresh token
    itself stayed valid for its full 14-day life if anyone had it."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_str = request.data.get("refresh", "")
        if refresh_str:
            try:
                jti = RefreshToken(refresh_str)["jti"]
                RefreshToken(refresh_str).blacklist()
                UserSession.objects.filter(outstanding_token__jti=jti).delete()
            except Exception:
                pass
        return Response({"detail": "Logged out."})


class SessionListView(generics.ListAPIView):
    """Every device the current user is signed in on."""
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        return UserSession.objects.filter(
            user=self.request.user,
            outstanding_token__blacklistedtoken__isnull=True,
            outstanding_token__expires_at__gt=timezone.now(),
        ).select_related("outstanding_token")


class SessionRevokeView(APIView):
    """Sign a specific device out immediately by blacklisting its
    refresh token — the next request from that device gets a 401 with
    no way to silently refresh past it."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = UserSession.objects.filter(id=session_id, user=request.user).select_related("outstanding_token").first()
        if not session:
            return Response({"detail": "Session not found."}, status=404)
        BlacklistedToken.objects.get_or_create(token=session.outstanding_token)
        session.delete()
        return Response({"detail": "Session revoked."})


class SessionRevokeOthersView(APIView):
    """'Sign out everywhere else' — revokes every session for this user
    except the one making the request (identified by session_id sent
    from the frontend's own stored value)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        keep_id = request.data.get("session_id")
        sessions = UserSession.objects.filter(user=request.user).select_related("outstanding_token")
        if keep_id:
            sessions = sessions.exclude(id=keep_id)
        count = 0
        for session in sessions:
            BlacklistedToken.objects.get_or_create(token=session.outstanding_token)
            session.delete()
            count += 1
        return Response({"revoked": count})


class BusinessStaffSessionsView(generics.ListAPIView):
    """Owner/admin view of every active session held by staff in this
    business — the list this owner needs before deciding whose session
    to revoke below. Not to be confused with SessionListView above,
    which only ever shows a user their own devices."""
    serializer_class = BusinessStaffSessionSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        member_user_ids = Membership.objects.filter(
            business_id=self.request.business_id, is_active=True,
        ).values_list("user_id", flat=True)
        return UserSession.objects.filter(
            user_id__in=member_user_ids,
            outstanding_token__blacklistedtoken__isnull=True,
            outstanding_token__expires_at__gt=timezone.now(),
        ).select_related("outstanding_token", "user")


class BusinessStaffSessionRevokeView(APIView):
    """Owner/admin revoking a specific staff member's session — not to
    be confused with SessionRevokeView above, which only ever lets a
    user revoke their own device."""
    permission_classes = [IsOwnerOrAdmin]

    def post(self, request, session_id):
        member_user_ids = Membership.objects.filter(
            business_id=request.business_id, is_active=True,
        ).values_list("user_id", flat=True)
        session = UserSession.objects.filter(
            id=session_id, user_id__in=member_user_ids,
        ).select_related("outstanding_token").first()
        if not session:
            return Response({"detail": "Session not found."}, status=404)
        BlacklistedToken.objects.get_or_create(token=session.outstanding_token)
        session.delete()
        return Response({"detail": "Session revoked."})


class AdminKillSwitchView(APIView):
    """Platform-staff emergency action: immediately revokes every
    active session for every member of a target business — for a
    reported compromise or breach, when there's no time to revoke
    devices one at a time. Distinct from BusinessStaffSessionRevokeView
    above, which is the owner's own single-device tool."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from apps.tenants.models import Business
        business_id = request.data.get("business_id")
        if not business_id:
            return Response({"detail": "business_id is required."}, status=400)
        business = generics.get_object_or_404(Business, id=business_id)

        member_user_ids = list(Membership.objects.filter(
            business_id=business_id, is_active=True,
        ).values_list("user_id", flat=True))
        sessions = UserSession.objects.filter(user_id__in=member_user_ids).select_related("outstanding_token")
        count = 0
        for session in sessions:
            BlacklistedToken.objects.get_or_create(token=session.outstanding_token)
            count += 1
        sessions.delete()

        log_action(
            business=business, actor=request.user, action="update",
            reason=f"EMERGENCY: platform support ({request.user.email}) revoked all {count} active session(s) for this business.",
        )
        return Response({"revoked": count})
    """Owner/admin-only: every active login session across all of this
    business's staff — who, on what device, from what IP, on which
    branch(es) they're a member of, and when they were last active.
    This is the 'main branch sees when a branch logs in and on what
    device' visibility — deliberately separate from SessionListView
    above, which only ever shows a user their own devices."""
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        from django.utils import timezone as tz
        memberships = (
            Membership.objects.filter(business_id=request.business_id, is_active=True)
            .select_related("user", "branch", "role")
        )
        by_user: dict = {}
        for m in memberships:
            by_user.setdefault(m.user_id, {"user": m.user, "role": m.role.name, "branches": []})
            by_user[m.user_id]["branches"].append(m.branch.name if m.branch else "All branches")

        sessions = (
            UserSession.objects.filter(
                user_id__in=by_user.keys(),
                outstanding_token__blacklistedtoken__isnull=True,
                outstanding_token__expires_at__gt=tz.now(),
            )
            .select_related("user", "outstanding_token")
            .order_by("-last_seen_at")
        )

        data = [
            {
                "id": str(s.id),
                "user_email": s.user.email,
                "user_name": (f"{s.user.first_name} {s.user.last_name}".strip() or s.user.email),
                "role": by_user[s.user_id]["role"],
                "branches": by_user[s.user_id]["branches"],
                "device_label": s.device_label,
                "ip_address": s.ip_address,
                "created_at": s.created_at,
                "last_seen_at": s.last_seen_at,
            }
            for s in sessions
        ]
        return Response(data)


# --- Two-factor authentication (TOTP) -----------------------------------
# Standard app-based 2FA (Google Authenticator, Authy, etc.) — no SMS
# provider needed. Setup is two steps (setup -> confirm) so an account
# can never get locked into 2FA with a secret the person never
# actually verified they could generate valid codes for.

PRE_AUTH_TOKEN_MAX_AGE = 300  # 5 minutes — long enough to type a code, short enough to matter


class TwoFactorSetupView(APIView):
    """Step 1: generate a new secret and QR code. NOT enabled yet —
    the secret is only returned here for the person to scan; it's
    saved to the user only once they prove they can generate a valid
    code, via TwoFactorConfirmView."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=request.user.email, issuer_name="Truvanta")
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        # Stashed on the session-equivalent (signed, not the DB) until
        # confirmed — avoids writing a secret to the user record that
        # was never actually verified to work.
        pending_token = TimestampSigner().sign(f"{request.user.id}:{secret}")
        return Response({"secret": secret, "qr_code": qr_data_uri, "pending_token": pending_token})


class TwoFactorConfirmView(APIView):
    """Step 2: prove the authenticator app actually works before 2FA
    is turned on. Only after this succeeds does the secret get saved
    and two_factor_enabled flip to True."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pending_token = request.data.get("pending_token", "")
        code = request.data.get("code", "")
        try:
            payload = TimestampSigner().unsign(pending_token, max_age=PRE_AUTH_TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return Response({"detail": "Setup expired — start again."}, status=400)
        user_id, secret = payload.split(":", 1)
        if str(request.user.id) != user_id:
            return Response({"detail": "Setup expired — start again."}, status=400)
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            return Response({"detail": "That code didn't match — check the time on your phone and try again."}, status=400)
        request.user.two_factor_secret = secret
        request.user.two_factor_enabled = True
        request.user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        return Response({"detail": "Two-factor authentication is now on."})


class TwoFactorDisableView(APIView):
    """Requires the current password — disabling 2FA is a
    security-reducing action and shouldn't be doable from just an
    already-open session (e.g. someone else at an unlocked computer)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.check_password(request.data.get("password", "")):
            return Response({"detail": "Incorrect password."}, status=400)
        request.user.two_factor_enabled = False
        request.user.two_factor_secret = ""
        request.user.save(update_fields=["two_factor_enabled", "two_factor_secret"])
        return Response({"detail": "Two-factor authentication is now off."})


class Verify2FALoginView(APIView):
    """Step 2 of login when 2FA is enabled — exchanges a valid
    pre_auth_token + TOTP code for real access/refresh tokens, and
    records the UserSession exactly like a normal login does."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request):
        pre_auth_token = request.data.get("pre_auth_token", "")
        code = request.data.get("code", "")
        try:
            user_id = TimestampSigner().unsign(pre_auth_token, max_age=PRE_AUTH_TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return Response({"detail": "Login expired — sign in again."}, status=400)

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id, two_factor_enabled=True)
        except User.DoesNotExist:
            return Response({"detail": "Login expired — sign in again."}, status=400)

        if not pyotp.TOTP(user.two_factor_secret).verify(code, valid_window=1):
            return Response({"detail": "That code didn't match."}, status=400)

        refresh = RefreshToken.for_user(user)
        data = {"access": str(refresh.access_token), "refresh": str(refresh)}
        data["session_id"] = _record_session(request, data["refresh"])
        _mark_real_login(user)
        _check_continuity_for_user(user)
        return Response(data)


class DuressPasswordView(APIView):
    """Set up or update the user's silent duress password (Security
    settings). Requires the real current password to confirm identity
    — see services.set_duress_password's docstring. GET reveals only
    whether one is configured (never anything else) so the Settings
    UI can say 'enabled' without ever exposing the value."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"is_set_up": bool(request.user.duress_password_hash)})

    def post(self, request):
        from .services import set_duress_password
        try:
            set_duress_password(
                user=request.user,
                real_password_confirmation=request.data.get("current_password", ""),
                new_duress_password=request.data.get("duress_password", ""),
            )
        except DjangoValidationError as e:
            return Response({"detail": str(e.message) if hasattr(e, "message") else str(e)}, status=400)
        return Response({"detail": "Duress password saved."})

    def delete(self, request):
        if not request.user.check_password(request.data.get("current_password", "")):
            return Response({"detail": "Your current password is incorrect."}, status=400)
        request.user.duress_password_hash = ""
        request.user.save(update_fields=["duress_password_hash"])
        return Response({"detail": "Duress password removed."})
