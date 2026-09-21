from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessCreateView, BusinessDetailView, BranchViewSet, RegenerateSignupCodeView,
    BranchJoinRequestCreateView, BranchJoinRequestListView,
    BranchJoinRequestApproveView, BranchJoinRequestRejectView,
    BusinessSupportAccessGrantView, BusinessSupportAccessRevokeView, AdminSupportLoginView,
)

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")

urlpatterns = [
    path("businesses/", BusinessCreateView.as_view(), name="business-create"),
    path("businesses/<uuid:pk>/", BusinessDetailView.as_view(), name="business-detail"),
    path("businesses/<uuid:business_id>/regenerate-signup-code/", RegenerateSignupCodeView.as_view(), name="business-regenerate-signup-code"),
    path("branch-join-requests/", BranchJoinRequestListView.as_view(), name="branch-join-request-list"),
    path("branch-join-requests/submit/", BranchJoinRequestCreateView.as_view(), name="branch-join-request-create"),
    path("branch-join-requests/<uuid:pk>/approve/", BranchJoinRequestApproveView.as_view(), name="branch-join-request-approve"),
    path("branch-join-requests/<uuid:pk>/reject/", BranchJoinRequestRejectView.as_view(), name="branch-join-request-reject"),
    path("support-access/grant/", BusinessSupportAccessGrantView.as_view(), name="support-access-grant"),
    path("support-access/revoke/", BusinessSupportAccessRevokeView.as_view(), name="support-access-revoke"),
    path("support-access/login/", AdminSupportLoginView.as_view(), name="support-access-login"),
    path("", include(router.urls)),
]
