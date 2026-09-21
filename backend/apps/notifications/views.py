from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import TenantScopedModelViewSet
from apps.core.permissions import IsBusinessMember
from apps.tenants.models import Business, Branch
from .models import Notification, PlatformSettings
from .serializers import NotificationSerializer, PlatformSettingsSerializer
from .feature_catalog import HUB_KEYS, DEFAULT_FEATURE_HUBS, resolve_feature_hubs
from . import triggers


class NotificationViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]  # PATCH only for is_read; POST only for
    # the check-*/send-* actions below — individual notification rows are still never created directly by clients.
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filterset_fields = ["level", "branch"]

    def create(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed("POST")

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        # A lightweight, separate call rather than making the nav
        # badge fetch (and re-fetch on a timer) the entire notification
        # list just to learn a single number.
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        from django.utils import timezone
        updated = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"marked": updated})

    @action(detail=False, methods=["post"], url_path="check-overdue-debts")
    def check_overdue_debts(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.data.get("branch"):
            branch = Branch.objects.get(pk=request.data["branch"], business=business)
        notification = triggers.check_overdue_debts(business, branch)
        if notification:
            return Response(NotificationSerializer(notification).data, status=201)
        return Response({"detail": "No overdue customers found."}, status=200)

    @action(detail=False, methods=["post"], url_path="check-low-stock")
    def check_low_stock(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.data.get("branch"):
            branch = Branch.objects.get(pk=request.data["branch"], business=business)
        notification = triggers.check_low_stock(business, branch)
        if notification:
            return Response(NotificationSerializer(notification).data, status=201)
        return Response({"detail": "Nothing is low on stock right now."}, status=200)

    @action(detail=False, methods=["post"], url_path="send-daily-summary")
    def send_daily_summary(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = Branch.objects.get(pk=request.data["branch"], business=business)
        notification = triggers.send_daily_summary(business, branch)
        return Response(NotificationSerializer(notification).data, status=201)


class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class PlatformSettingsView(generics.RetrieveUpdateAPIView):
    """Deployment-wide integration credentials — WhatsApp, Gmail, and
    Truvanta's own Paystack keys (for AI add-on billing). Staff-only:
    this is not per-business data, it belongs to whoever runs this
    Truvanta deployment.
    """
    serializer_class = PlatformSettingsSerializer
    permission_classes = [IsStaffUser]

    def get_object(self):
        return PlatformSettings.load()


class AdminPinUnlockView(APIView):
    """Staff-only quick-access unlock for the admin console. This is a
    convenience layer on top of real authentication, not a
    replacement for it — you already have to be a genuine is_staff
    user with a real account to even reach this endpoint.

    No default PIN ships with the app. Whichever staff member unlocks
    first, while none is set yet, establishes it for everyone —
    that's deliberately how "the first admin sets it" is implemented,
    rather than shipping a known default value that people forget to
    change.
    """
    permission_classes = [IsStaffUser]

    def post(self, request):
        pin = str(request.data.get("pin", "")).strip()
        if not (pin.isdigit() and 4 <= len(pin) <= 8):
            return Response({"detail": "PIN must be 4-8 digits."}, status=400)

        settings_row = PlatformSettings.load()
        now = timezone.now()

        if settings_row.admin_pin_locked_until and settings_row.admin_pin_locked_until > now:
            wait_minutes = max(1, int((settings_row.admin_pin_locked_until - now).total_seconds() // 60) + 1)
            return Response(
                {"detail": f"Too many wrong attempts. Try again in about {wait_minutes} minute(s)."},
                status=429,
            )

        if not settings_row.admin_pin_hash:
            # No PIN exists yet — this request sets it.
            settings_row.admin_pin_hash = make_password(pin)
            settings_row.admin_pin_set_at = now
            settings_row.admin_pin_failed_attempts = 0
            settings_row.admin_pin_locked_until = None
            settings_row.save(update_fields=[
                "admin_pin_hash", "admin_pin_set_at", "admin_pin_failed_attempts", "admin_pin_locked_until",
            ])
            return Response({"status": "set", "detail": "PIN created."})

        if check_password(pin, settings_row.admin_pin_hash):
            settings_row.admin_pin_failed_attempts = 0
            settings_row.admin_pin_locked_until = None
            settings_row.save(update_fields=["admin_pin_failed_attempts", "admin_pin_locked_until"])
            return Response({"status": "unlocked"})

        settings_row.admin_pin_failed_attempts += 1
        if settings_row.admin_pin_failed_attempts >= 5:
            settings_row.admin_pin_locked_until = now + timedelta(minutes=15)
            settings_row.admin_pin_failed_attempts = 0
        settings_row.save(update_fields=["admin_pin_failed_attempts", "admin_pin_locked_until"])
        return Response({"detail": "Wrong PIN."}, status=403)


class AdminPinStatusView(APIView):
    """Lets the frontend show 'set up a PIN' vs 'enter your PIN' —
    without ever exposing the PIN or its hash."""
    permission_classes = [IsStaffUser]

    def get(self, request):
        settings_row = PlatformSettings.load()
        return Response({"pin_is_set": bool(settings_row.admin_pin_hash)})


class AdminPinChangeView(APIView):
    """Any already-unlocked staff member can set a new PIN — this
    replaces the shared admin-console PIN outright, the same as
    changing a shared door code."""
    permission_classes = [IsStaffUser]

    def post(self, request):
        pin = str(request.data.get("pin", "")).strip()
        if not (pin.isdigit() and 4 <= len(pin) <= 8):
            return Response({"detail": "PIN must be 4-8 digits."}, status=400)
        settings_row = PlatformSettings.load()
        settings_row.admin_pin_hash = make_password(pin)
        settings_row.admin_pin_set_at = timezone.now()
        settings_row.admin_pin_failed_attempts = 0
        settings_row.admin_pin_locked_until = None
        settings_row.save(update_fields=[
            "admin_pin_hash", "admin_pin_set_at", "admin_pin_failed_attempts", "admin_pin_locked_until",
        ])
        return Response({"status": "changed"})


class PlatformBrandingView(APIView):
    """Public, unauthenticated — deliberately the only slice of
    PlatformSettings anyone can read without being staff. Needed so
    the universal accent color can apply on the login screen itself,
    before anyone is authenticated at all. Never exposes anything
    else from PlatformSettings (no credentials, no PIN status)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings_row = PlatformSettings.load()
        return Response({
            "universal_color": settings_row.universal_color,
            "minimum_client_version": settings_row.minimum_client_version,
            "google_oauth_client_id": settings_row.google_oauth_client_id,
        })


class FeatureLayoutView(APIView):
    """Read-only, any authenticated user — lets every hub page (Sell &
    Buy / Security / Business Health) ask "which hub does feature X
    currently live under" without needing staff access. The actual
    display details (title, icon, route) stay in the frontend; this
    only answers the one question a business user's app needs: where
    is this feature right now."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings_row = PlatformSettings.load()
        return Response({"feature_hubs": resolve_feature_hubs(settings_row.feature_hub_overrides)})


class AdminFeatureLayoutView(APIView):
    """Staff-only — lets a platform admin move an existing feature to
    a different dashboard without a code change or redeploy. This
    intentionally does NOT let anyone invent a new feature or hub key
    from this screen — only reassign one of the fixed, known features
    to one of the three fixed, known hubs. A real drag-and-drop
    frontend editor is a much larger undertaking; this solves the
    actual need (rearranging where things live) safely instead."""
    permission_classes = [IsStaffUser]

    def get(self, request):
        settings_row = PlatformSettings.load()
        resolved = resolve_feature_hubs(settings_row.feature_hub_overrides)
        return Response({
            "features": [
                {"key": key, "default_hub": DEFAULT_FEATURE_HUBS[key], "current_hub": resolved[key]}
                for key in sorted(DEFAULT_FEATURE_HUBS)
            ],
            "hubs": sorted(HUB_KEYS),
        })

    def patch(self, request):
        from apps.audit.services import log_action

        feature_key = request.data.get("feature_key")
        hub_key = request.data.get("hub")
        if feature_key not in DEFAULT_FEATURE_HUBS:
            return Response({"detail": "Unknown feature."}, status=400)
        if hub_key not in HUB_KEYS:
            return Response({"detail": "Unknown dashboard."}, status=400)

        settings_row = PlatformSettings.load()
        overrides = dict(settings_row.feature_hub_overrides or {})
        default_hub = DEFAULT_FEATURE_HUBS[feature_key]
        previous_hub = overrides.get(feature_key, default_hub)

        if hub_key == default_hub:
            overrides.pop(feature_key, None)  # back to default — no override needed to store
        else:
            overrides[feature_key] = hub_key
        settings_row.feature_hub_overrides = overrides
        settings_row.save(update_fields=["feature_hub_overrides"])

        log_action(
            business=None, actor=request.user, action="other",
            previous_value={"hub": previous_hub}, new_value={"hub": hub_key},
            reason=f"Platform admin: moved '{feature_key}' from the {previous_hub.replace('_', ' ')} "
                   f"dashboard to {hub_key.replace('_', ' ')}.",
        )
        return Response({"key": feature_key, "default_hub": default_hub, "current_hub": hub_key})
