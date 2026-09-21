from django.urls import path

from .views import AuditLogListView, StaffIntegrityView, AdminAuditLogListView

urlpatterns = [
    path("audit-logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("staff-integrity/", StaffIntegrityView.as_view(), name="staff-integrity"),
    path("admin/audit-logs/", AdminAuditLogListView.as_view(), name="admin-audit-log-list"),
]
