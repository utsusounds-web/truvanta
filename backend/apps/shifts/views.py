from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from rest_framework.response import Response

from apps.core.permissions import IsBusinessMember
from apps.tenants.models import Branch
from .models import Shift
from .serializers import ShiftSerializer, ShiftOpenSerializer, ShiftCloseSerializer
from . import services


class ShiftViewSet(viewsets.ModelViewSet):
    permission_classes = [IsBusinessMember]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ShiftSerializer
    filterset_fields = ["branch", "status", "employee"]

    def get_queryset(self):
        qs = Shift.objects.filter(business_id=self.request.business_id).select_related("branch", "employee")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(branch_id__in=accessible)
        return qs

    def create(self, request, *args, **kwargs):
        s = ShiftOpenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        branch = Branch.objects.get(pk=s.validated_data["branch"], business_id=request.business_id)
        accessible = request.accessible_branch_ids
        if accessible is not None and branch.id not in accessible:
            raise DRFPermissionDenied("You don't have access to that branch.")
        try:
            shift = services.open_shift(
                business=branch.business, branch=branch, employee=request.user,
                opening_cash=s.validated_data["opening_cash"],
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(ShiftSerializer(shift).data, status=201)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        shift = self.get_object()
        s = ShiftCloseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            shift = services.close_shift(
                shift=shift, closing_physical_cash=s.validated_data["closing_physical_cash"], actor=request.user,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(ShiftSerializer(shift).data)

    @action(detail=True, methods=["get"], url_path="closing-report-pdf")
    def closing_report_pdf(self, request, pk=None):
        from .documents import generate_shift_closing_pdf
        shift = self.get_object()
        pdf_bytes = generate_shift_closing_pdf(shift)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="shift-closing-{str(shift.id)[:8]}.pdf"'
        return response
