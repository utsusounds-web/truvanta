from django.contrib import admin
from .models import Notification, PlatformSettings


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "business", "whatsapp_delivered", "email_delivered", "created_at")
    list_filter = ("level", "whatsapp_delivered", "email_delivered")


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "updated_at")

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()
