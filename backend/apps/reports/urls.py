from django.urls import path
from .views import (
    OwnerDashboardView, WhereDidMyMoneyGoView, BusinessHealthView, RiskAlertsView, SalesTrendView,
    InventoryProfitabilityView, StatementExportView, DebtAgingView, DailyPrioritiesView,
)

urlpatterns = [
    path("owner-dashboard/", OwnerDashboardView.as_view(), name="owner-dashboard"),
    path("sales-trend/", SalesTrendView.as_view(), name="sales-trend"),
    path("where-did-my-money-go/", WhereDidMyMoneyGoView.as_view(), name="money-go"),
    path("business-health/", BusinessHealthView.as_view(), name="business-health"),
    path("risk-alerts/", RiskAlertsView.as_view(), name="risk-alerts"),
    path("inventory-profitability/", InventoryProfitabilityView.as_view(), name="inventory-profitability"),
    path("statements/", StatementExportView.as_view(), name="statement-export"),
    path("debt-aging/", DebtAgingView.as_view(), name="debt-aging"),
    path("daily-priorities/", DailyPrioritiesView.as_view(), name="daily-priorities"),
]
