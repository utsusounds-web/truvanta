from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LoanReadinessReportViewSet, LoanReadinessVerifyView

router = DefaultRouter()
router.register("loan-readiness-reports", LoanReadinessReportViewSet, basename="loan-readiness-report")

urlpatterns = router.urls + [
    path("verify-loan-report/<uuid:report_id>/", LoanReadinessVerifyView.as_view(), name="loan-readiness-verify"),
]
