from django.http import HttpResponse
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.permissions import HasBusinessPermission
from apps.tenants.models import Business
from .models import LoanReadinessReport
from .serializers import LoanReadinessReportSerializer
from . import services
from .documents import generate_loan_readiness_pdf


class RequireViewProfit(HasBusinessPermission):
    required_permission_code = "view_profit"


class LoanReadinessReportViewSet(ReadOnlyModelViewSet):
    """Read-only + a 'generate' action, deliberately — a report is
    never edited, only created fresh (see the model's docstring on
    why immutability is what makes the QR verification meaningful)."""
    permission_classes = [RequireViewProfit]
    serializer_class = LoanReadinessReportSerializer

    def get_queryset(self):
        return LoanReadinessReport.objects.filter(business_id=self.request.business_id)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        business = Business.objects.get(pk=request.business_id)
        months = int(request.data.get("months", 12))
        snapshot = services.generate_snapshot(business=business, months=months)
        report = LoanReadinessReport.objects.create(
            business=business, generated_by=request.user,
            period_start=snapshot["period_start"], period_end=snapshot["period_end"],
            snapshot_json=snapshot,
        )
        return Response(LoanReadinessReportSerializer(report).data, status=201)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        report = self.get_object()
        pdf_bytes = generate_loan_readiness_pdf(report)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="loan-readiness-{str(report.id)[:8]}.pdf"'
        return response


class LoanReadinessVerifyView(APIView):
    """Public verification (the QR code on the PDF points here) — a
    lender scans this to confirm the document matches what was
    actually generated. Returns exactly the summary figures already
    printed on the PDF (this document exists specifically to be shown
    to a lender, so there's nothing here a lender wasn't already
    handed on paper) — never anything beyond that, and never live
    data, so it can never drift from what's printed.
    """
    permission_classes = [AllowAny]

    def get(self, request, report_id):
        try:
            report = LoanReadinessReport.objects.select_related("business").get(pk=report_id)
        except LoanReadinessReport.DoesNotExist:
            return Response({"valid": False}, status=404)
        snap = report.snapshot_json
        return Response({
            "valid": True,
            "business_name": snap.get("business_name"),
            "generated_at": snap.get("generated_at"),
            "period_start": snap.get("period_start"),
            "period_end": snap.get("period_end"),
            "total_revenue": snap.get("total_revenue"),
            "gross_margin_percent": snap.get("gross_margin_percent"),
            "currency_code": snap.get("currency_code"),
        })
