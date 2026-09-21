from django.contrib import admin

from .models import BillingEvent, Feature, FeatureOverride, Plan, Subscription


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "category", "is_active"]
    search_fields = ["key", "name"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_amount", "currency", "billing_interval", "is_active", "sort_order"]
    filter_horizontal = ["features"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["business", "plan", "status", "current_period_end", "cancel_at_period_end"]
    list_filter = ["status"]
    search_fields = ["business__name"]


@admin.register(FeatureOverride)
class FeatureOverrideAdmin(admin.ModelAdmin):
    list_display = ["business", "feature", "is_enabled", "expires_at", "granted_by"]
    list_filter = ["is_enabled"]
    search_fields = ["business__name", "feature__key"]


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "business", "processed_ok", "created_at"]
    list_filter = ["event_type", "processed_ok"]
    readonly_fields = [f.name for f in BillingEvent._meta.fields]
