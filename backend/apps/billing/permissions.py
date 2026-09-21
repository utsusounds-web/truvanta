from rest_framework.permissions import BasePermission

from apps.core.permissions import IsBusinessMember

from .services import business_has_feature


class IsPlatformAdmin(BasePermission):
    """Gate for the platform-owner controls (managing Plans, Features,
    viewing all businesses' subscriptions, granting overrides) — this
    is you running the deployment, not a business owner. Backed by
    Django's built-in is_staff, same as PlatformSettingsView.
    """

    message = "Platform admin access required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class HasFeature(IsBusinessMember):
    """Subclass and set `required_feature_key` to gate a view behind a
    paid feature. Requires business membership (like IsBusinessMember)
    AND that the business currently has the feature, via subscription
    or admin override.
    """

    required_feature_key = None
    message = "This feature is not included in your current plan."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        key = self.required_feature_key or getattr(view, "required_feature_key", None)
        if not key:
            return True
        return business_has_feature(request.business_id, key)
