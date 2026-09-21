from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import RecurringExpenseScheduleViewSet, CashFlowForecastView

router = DefaultRouter()
router.register("recurring-expense-schedules", RecurringExpenseScheduleViewSet, basename="recurring-expense-schedule")

urlpatterns = router.urls + [
    path("cash-flow-forecast/", CashFlowForecastView.as_view(), name="cash-flow-forecast"),
]
