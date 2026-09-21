from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "business", "actor", "action", "branch")
    list_filter = ("action", "business")
    search_fields = ("reason",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
