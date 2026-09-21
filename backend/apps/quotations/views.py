import random
import string

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.core.permissions import IsBusinessMember
from apps.core.viewsets import TenantScopedModelViewSet
from apps.tenants.models import Branch
from .models import Quotation, QuotationItem
from .serializers import QuotationSerializer, QuotationItemSerializer, ConvertToSaleSerializer
from . import services


def _generate_reference(business, prefix):
    for _ in range(10):
        candidate = f"{prefix}-{''.join(random.choices(string.digits, k=6))}"
        if not Quotation.objects.filter(business=business, reference_number=candidate).exists():
            return candidate
    raise DjangoValidationError("Couldn't generate a unique reference number — try again.")


class QuotationViewSet(TenantScopedModelViewSet):
    # Any business member can quote a customer, same as ringing up a
    # sale — this isn't gated behind a granular permission because
    # nothing here touches stock or money until it's converted, at
    # which point normal sale-creation rules apply anyway.
    permission_classes = [IsBusinessMember]
    queryset = Quotation.objects.select_related("branch", "customer", "created_by").prefetch_related("items__product", "items__unit")
    serializer_class = QuotationSerializer
    filterset_fields = ["status", "document_type", "branch", "customer"]

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(branch_id__in=accessible)
        return qs

    def list(self, request, *args, **kwargs):
        from apps.tenants.models import Business
        services.mark_expired_quotations(Business.objects.get(pk=request.business_id))
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        branch = serializer.validated_data["branch"]
        prefix = "PF" if serializer.validated_data.get("document_type") == "proforma_invoice" else "QT"
        reference = _generate_reference(branch.business, prefix)
        serializer.save(business_id=self.request.business_id, created_by=self.request.user, reference_number=reference)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status == "converted":
            raise DRFValidationError("A converted quotation can't be voided — void or return the resulting sale instead.")
        quotation.status = "void"
        quotation.save(update_fields=["status"])
        return Response(QuotationSerializer(quotation).data)

    @action(detail=True, methods=["post"])
    def mark_sent(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status != "draft":
            raise DRFValidationError("Only a draft quotation can be marked sent.")
        quotation.status = "sent"
        quotation.save(update_fields=["status"])
        return Response(QuotationSerializer(quotation).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        quotation = self.get_object()
        input_serializer = ConvertToSaleSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        shift = None
        if data.get("shift"):
            from apps.shifts.models import Shift
            shift = Shift.objects.get(pk=data["shift"], business_id=request.business_id)

        try:
            sale = services.convert_to_sale(
                quotation=quotation, cashier=request.user, payments=data.get("payments", []),
                sale_type=data["sale_type"], shift=shift,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))

        from apps.sales.serializers import SaleSerializer
        return Response(SaleSerializer(sale).data, status=201)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        quotation = self.get_object()
        from .documents import generate_quotation_pdf
        pdf_bytes = generate_quotation_pdf(quotation)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{quotation.reference_number}.pdf"'
        return response


class QuotationItemViewSet(TenantScopedModelViewSet):
    permission_classes = [IsBusinessMember]
    queryset = QuotationItem.objects.select_related("quotation", "product", "unit")
    serializer_class = QuotationItemSerializer
    filterset_fields = ["quotation"]

    def perform_create(self, serializer):
        quotation = serializer.validated_data["quotation"]
        if quotation.status not in ("draft",):
            raise DRFValidationError("Items can only be added while the quotation is still a draft.")
        serializer.save(business_id=self.request.business_id)
