from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet, PlatformSettingsView,
    AdminPinUnlockView, AdminPinStatusView, AdminPinChangeView, PlatformBrandingView,
    FeatureLayoutView, AdminFeatureLayoutView,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
urlpatterns = router.urls + [
    path("platform-settings/", PlatformSettingsView.as_view(), name="platform-settings"),
    path("platform-branding/", PlatformBrandingView.as_view(), name="platform-branding"),
    path("feature-layout/", FeatureLayoutView.as_view(), name="feature-layout"),
    path("admin/feature-layout/", AdminFeatureLayoutView.as_view(), name="admin-feature-layout"),
    path("admin-pin/status/", AdminPinStatusView.as_view(), name="admin-pin-status"),
    path("admin-pin/unlock/", AdminPinUnlockView.as_view(), name="admin-pin-unlock"),
    path("admin-pin/change/", AdminPinChangeView.as_view(), name="admin-pin-change"),
]
