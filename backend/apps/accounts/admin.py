from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, Role, Permission, RolePermission, Membership


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("email", "username", "is_active", "is_staff")
    ordering = ("email",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        (None, {"fields": ("phone_number",)}),
    )


admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(Membership)
