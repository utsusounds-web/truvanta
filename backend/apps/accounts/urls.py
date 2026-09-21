from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import ScopedRateThrottle

from .views import (
    RegisterView, MeView, PermissionListView, RoleViewSet, MembershipViewSet, StaffInviteView,
    PasswordResetRequestView, PasswordResetConfirmView,
    SessionAwareTokenObtainPairView, SessionAwareTokenRefreshView, LogoutView,
    SessionListView, SessionRevokeView, SessionRevokeOthersView, BusinessStaffSessionsView, BusinessStaffSessionRevokeView,
    AdminKillSwitchView,
    TwoFactorSetupView, TwoFactorConfirmView, TwoFactorDisableView, Verify2FALoginView, DuressPasswordView,
    GoogleLoginView,
)


class ThrottledTokenObtainPairView(SessionAwareTokenObtainPairView):
    """Same login endpoint, with a tight rate limit — this is the
    endpoint a credential-stuffing attempt would hammer."""
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]


router = DefaultRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("memberships", MembershipViewSet, basename="membership")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", SessionAwareTokenRefreshView.as_view(), name="token_refresh"),
    path("login/verify-2fa/", Verify2FALoginView.as_view(), name="verify-2fa-login"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/confirm/", TwoFactorConfirmView.as_view(), name="2fa-confirm"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("duress-password/", DuressPasswordView.as_view(), name="duress-password"),
    path("me/", MeView.as_view(), name="me"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
    path("staff/invite/", StaffInviteView.as_view(), name="staff-invite"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("sessions/", SessionListView.as_view(), name="session-list"),
    path("sessions/<uuid:session_id>/revoke/", SessionRevokeView.as_view(), name="session-revoke"),
    path("sessions/revoke-others/", SessionRevokeOthersView.as_view(), name="session-revoke-others"),
    path("business-sessions/", BusinessStaffSessionsView.as_view(), name="business-sessions"),
    path("business-sessions/<uuid:session_id>/revoke/", BusinessStaffSessionRevokeView.as_view(), name="business-session-revoke"),
    path("admin/kill-switch/", AdminKillSwitchView.as_view(), name="admin-kill-switch"),
    path("", include(router.urls)),
]
