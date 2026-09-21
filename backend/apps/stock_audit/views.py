from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from apps.core.permissions import IsBusinessMember
from apps.tenants.models import Branch
from .models import QuickAudit
from .serializers import QuickAuditSerializer
from . import services


class QuickAuditViewSet(viewsets.ModelViewSet):
    permission_classes = [IsBusinessMember]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = QuickAuditSerializer

    def get_queryset(self):
        qs = QuickAudit.objects.filter(business_id=self.request.business_id).prefetch_related("lines__product")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(branch_id__in=accessible)
        return qs

    def create(self, request, *args, **kwargs):
        branch = Branch.objects.get(pk=request.data.get("branch"), business_id=request.business_id)
        accessible = request.accessible_branch_ids
        if accessible is not None and branch.id not in accessible:
            raise DRFPermissionDenied("You don't have access to that branch.")
        sample_size = int(request.data.get("sample_size", 5))
        try:
            audit = services.trigger_quick_audit(
                business=branch.business, branch=branch, triggered_by=request.user, sample_size=sample_size,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(QuickAuditSerializer(audit).data, status=201)

    @action(detail=True, methods=["post"])
    def record_counts(self, request, pk=None):
        audit = self.get_object()
        counts = request.data.get("counts", {})
        try:
            updated = services.record_counts(audit=audit, counts=counts, counted_by=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(QuickAuditSerializer(updated).data)
