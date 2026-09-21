from django.contrib import admin
from .models import StockLevel, StockMovement, StockTransfer

admin.site.register(StockLevel)
admin.site.register(StockTransfer)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "branch", "quantity_delta", "reason", "created_at")
    list_filter = ("reason", "branch")
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False
