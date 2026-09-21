from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from apps.core.viewsets import TenantScopedModelViewSet, BranchScopedModelViewSet
from apps.core.permissions import HasBusinessPermission
from .models import SaleReturn, SupplierReturn
from .serializers import SaleReturnSerializer, SupplierReturnSerializer
from . import services


class RequireApproveReturns(HasBusinessPermission):
    required_permission_code = "approve_returns"


class SaleReturnViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = SaleReturn.objects.select_related("sale", "sale_item")
    serializer_class = SaleReturnSerializer
    filterset_fields = ["sale", "status", "return_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(sale__branch_id__in=accessible)
        return qs

    def perform_create(self, serializer):
        sale = serializer.validated_data.get("sale")
        accessible = self.request.accessible_branch_ids
        if sale and accessible is not None and sale.branch_id not in accessible:
            raise DRFPermissionDenied("You don't have access to that branch.")
        instance = serializer.save(business_id=self.request.business_id, requested_by=self.request.user)
        services.notify_if_large_refund_while_away(instance)

    @action(detail=True, methods=["post"], permission_classes=[RequireApproveReturns])
    def approve(self, request, pk=None):
        sale_return = self.get_object()
        try:
            sale_return = services.approve_return(sale_return=sale_return, actor=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(SaleReturnSerializer(sale_return).data)


class SupplierReturnViewSet(BranchScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = SupplierReturn.objects.all()
    serializer_class = SupplierReturnSerializer

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        self._check_branch_access(branch)
        serializer.save(business_id=self.request.business_id, requested_by=self.request.user)
