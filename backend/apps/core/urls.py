from django.urls import path

from .views import LatestBackupView, GlobalSearchView

urlpatterns = [
    path("backups/latest/", LatestBackupView.as_view(), name="latest-backup"),
    path("search/", GlobalSearchView.as_view(), name="global-search"),
]
