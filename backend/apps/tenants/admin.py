from django.contrib import admin

from .models import Business, Branch


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "business_type", "currency_code", "is_active", "owner")
    search_fields = ("name", "email", "phone_number")
    list_filter = ("business_type", "is_active")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "is_active")
    list_filter = ("is_active",)
