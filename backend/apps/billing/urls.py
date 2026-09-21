from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"admin/features", views.FeatureAdminViewSet, basename="billing-admin-feature")
router.register(r"admin/plans", views.PlanAdminViewSet, basename="billing-admin-plan")
router.register(r"admin/overrides", views.FeatureOverrideAdminViewSet, basename="billing-admin-override")
router.register(r"admin/events", views.BillingEventAdminViewSet, basename="billing-admin-event")

urlpatterns = [
    path("plans/", views.PlanListView.as_view(), name="billing-plans"),
    path("subscription/", views.MySubscriptionView.as_view(), name="billing-my-subscription"),
    path("subscription/subscribe/", views.SubscribeView.as_view(), name="billing-subscribe"),
    path("subscription/cancel/", views.CancelSubscriptionView.as_view(), name="billing-cancel"),
    path("webhook/paystack/", views.PaystackWebhookView.as_view(), name="billing-webhook"),
    path("admin/subscriptions/", views.AdminSubscriptionListView.as_view(), name="billing-admin-subscriptions"),
    path("admin/subscriptions/activate/", views.AdminActivateSubscriptionView.as_view(), name="billing-admin-activate-subscription"),
    path("admin/tenants/<uuid:business_id>/usage/", views.AdminTenantUsageView.as_view(), name="billing-admin-tenant-usage"),
    path("admin/businesses/schedule-deletion/", views.AdminScheduleDeletionView.as_view(), name="billing-admin-schedule-deletion"),
    path("admin/businesses/cancel-deletion/", views.AdminCancelDeletionView.as_view(), name="billing-admin-cancel-deletion"),
    path("admin/businesses/execute-purge/", views.AdminExecutePurgeView.as_view(), name="billing-admin-execute-purge"),
    path("admin/subscriptions/extend-trial/", views.AdminExtendTrialView.as_view(), name="billing-admin-extend-trial"),
    path("admin/businesses/freeze/", views.AdminFreezeAccountView.as_view(), name="billing-admin-freeze"),
    path("admin/businesses/", views.AdminBusinessLookupView.as_view(), name="billing-admin-businesses"),
    path("admin/usage-analytics/", views.AdminUsageAnalyticsView.as_view(), name="billing-admin-usage-analytics"),
    path("admin/broadcast-notification/", views.AdminBroadcastNotificationView.as_view(), name="billing-admin-broadcast"),
    path("", include(router.urls)),
]
