from django.urls import path

from .views import ContinuitySettingsView, ContinuityStatusView

urlpatterns = [
    path("continuity/settings/", ContinuitySettingsView.as_view(), name="continuity-settings"),
    path("continuity/status/", ContinuityStatusView.as_view(), name="continuity-status"),
]
