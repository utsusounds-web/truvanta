from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasBusinessPermission
from apps.core.viewsets import TenantScopedModelViewSet
from .models import RecurringExpenseSchedule
from .serializers import RecurringExpenseScheduleSerializer
from . import services


class RequireViewProfit(HasBusinessPermission):
    required_permission_code = "view_profit"


class RecurringExpenseScheduleViewSet(TenantScopedModelViewSet):
    # Same tier as everything else financial/forward-looking about
    # the business — an owner declaring "rent is 200,000 on the 1st"
    # is exactly the kind of figure view_profit already gates.
    permission_classes = [RequireViewProfit]
    queryset = RecurringExpenseSchedule.objects.select_related("category", "branch")
    serializer_class = RecurringExpenseScheduleSerializer
    filterset_fields = ["is_active", "branch"]


class CashFlowForecastView(APIView):
    permission_classes = [RequireViewProfit]

    def get(self, request):
        from apps.tenants.models import Business, Branch
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        days_ahead = int(request.query_params.get("days_ahead", 30))
        return Response(services.cash_flow_forecast(business=business, branch=branch, days_ahead=days_ahead))
