from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied as DRFPermissionDenied
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.core.permissions import IsBusinessMember, HasBusinessPermission, IsOwnerOrAdmin
from apps.products.models import Product, UnitOfMeasure
from apps.tenants.models import Branch
from apps.customers.models import Customer
from apps.shifts.models import Shift
from apps.core.viewsets import TenantScopedModelViewSet
from .models import Sale, ReceiptPrintLog, Payment, ExchangeRate, PaymentMethod
from .serializers import (
    SaleSerializer, SaleCreateSerializer, ReceiptPrintLogListSerializer, PaymentReconciliationListSerializer,
    ExchangeRateSerializer, PaymentMethodSerializer,
)
from . import services
from .documents import generate_receipt_pdf
from apps.reports.exports import sales_csv


class SaleVerifyView(APIView):
    """Public receipt verification (the QR code on every printed
    receipt points here) — confirms a receipt is genuine without
    exposing anything sensitive: no customer info, no cashier name,
    no line items, no business financials."""
    permission_classes = [AllowAny]

    def get(self, request, sale_id):
        try:
            sale = Sale.objects.select_related("business", "branch").get(pk=sale_id)
        except Sale.DoesNotExist:
            return Response({"valid": False}, status=404)
        return Response({
            "valid": True,
            "transaction_number": sale.transaction_number,
            "business_name": sale.business.name,
            "branch_name": sale.branch.name,
            "date": sale.created_at.date().isoformat(),
            "grand_total": str(sale.grand_total),
            "currency": sale.business.currency_code,
            "status": sale.status,
        })


class RequireCancelSales(HasBusinessPermission):
    required_permission_code = "cancel_sales"


class SaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsBusinessMember]
    http_method_names = ["get", "post", "head", "options"]  # no destroy/patch — use cancel/return flows
    serializer_class = SaleSerializer
    filterset_fields = ["branch", "status", "customer", "sale_type"]
    # search_fields powers ?search= (rest_framework.filters.SearchFilter, enabled
    # globally in settings). This is the receipt-code lookup: a walk-in/irregular
    # customer never has a Customer record, so the only way staff can find their
    # sale later (for a return, a reprint, a dispute) is by the transaction_number
    # printed on their receipt. Without this, ?search= on this endpoint was a
    # silent no-op — the filter backend was enabled globally but no fields were
    # ever declared for it here.
    search_fields = ["transaction_number"]

    def get_queryset(self):
        qs = Sale.objects.filter(business_id=self.request.business_id).select_related(
            "branch", "cashier", "customer"
        ).prefetch_related("items", "payments", "print_logs")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(branch_id__in=accessible)
        return qs

    def create(self, request, *args, **kwargs):
        input_serializer = SaleCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        branch = Branch.objects.get(pk=data["branch"], business_id=request.business_id)
        accessible = request.accessible_branch_ids
        if accessible is not None and branch.id not in accessible:
            raise DRFPermissionDenied("You don't have access to that branch.")
        customer = None
        if data.get("customer"):
            customer = Customer.objects.get(pk=data["customer"], business_id=request.business_id)
        shift = None
        if data.get("shift"):
            shift = Shift.objects.get(pk=data["shift"], business_id=request.business_id)

        items = []
        for raw in data["items"]:
            items.append({
                "product": Product.objects.get(pk=raw["product"], business_id=request.business_id),
                "unit": UnitOfMeasure.objects.get(pk=raw["unit"], business_id=request.business_id),
                "quantity": raw["quantity"],
                "unit_price": raw["unit_price"],
                "discount_amount": raw["discount_amount"],
            })

        try:
            sale = services.create_sale(
                business=branch.business, branch=branch, cashier=request.user,
                items=items, payments=data["payments"], customer=customer,
                sale_type=data["sale_type"], shift=shift, note=data["note"], tax_total=data["tax_total"],
                client_reference=data.get("client_reference") or None,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(e.message if hasattr(e, "message") else str(e))

        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return sales_csv(qs)

    @action(detail=True, methods=["post"], permission_classes=[RequireCancelSales])
    def cancel(self, request, pk=None):
        sale = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            raise DRFValidationError({"reason": "A reason is required to cancel a sale."})
        try:
            sale = services.cancel_sale(sale=sale, actor=request.user, reason=reason)
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(SaleSerializer(sale).data)

    @action(detail=True, methods=["post"])
    def reprint_receipt(self, request, pk=None):
        sale = self.get_object()
        log = services.reprint_receipt(sale=sale, actor=request.user)
        return Response({"copy_number": log.copy_number, "is_reprint": log.copy_number > 1})

    @action(detail=True, methods=["get"], url_path="receipt-pdf")
    def receipt_pdf(self, request, pk=None):
        """Download the receipt as PDF, branded with the business's
        logo/name/address/footer. Pass ?reprint=1 to log and mark it
        as a reprint (per spec section 8)."""
        sale = self.get_object()
        copy_number = 1
        if request.query_params.get("reprint") == "1":
            log = services.reprint_receipt(sale=sale, actor=request.user)
            copy_number = log.copy_number
        else:
            last = sale.print_logs.order_by("-copy_number").first()
            copy_number = last.copy_number if last else 1
        pdf_bytes = generate_receipt_pdf(sale, copy_number)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{sale.transaction_number}.pdf"'
        return response

    @action(detail=True, methods=["get"], url_path="invoice-pdf")
    def invoice_pdf(self, request, pk=None):
        """A formal A4 invoice for the same sale — see
        sales.documents.generate_invoice_pdf for why this is a
        separate document from the thermal receipt."""
        from .documents import generate_invoice_pdf
        sale = self.get_object()
        pdf_bytes = generate_invoice_pdf(sale)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="invoice-{sale.transaction_number}.pdf"'
        return response


class ReceiptPrintLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Standalone browser for every receipt print/reprint across the
    business — separate from the per-sale list embedded in
    SaleSerializer, for a dedicated history screen."""
    permission_classes = [IsBusinessMember]
    serializer_class = ReceiptPrintLogListSerializer
    filterset_fields = ["sale"]

    def get_queryset(self):
        qs = ReceiptPrintLog.objects.filter(business_id=self.request.business_id).select_related(
            "sale", "sale__branch", "printed_by"
        ).order_by("-created_at")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(sale__branch_id__in=accessible)
        return qs


class PaymentReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    """Standalone queue for reconciling bank transfer/card/other
    payments against a bank or processor statement (spec section 20).
    Cash payments are confirmed automatically at creation — see
    Payment.save() — so they never appear here needing action."""
    permission_classes = [IsBusinessMember]
    serializer_class = PaymentReconciliationListSerializer
    filterset_fields = ["reconciliation_status", "method", "sale__branch"]

    def get_queryset(self):
        qs = Payment.objects.filter(business_id=self.request.business_id).select_related(
            "sale", "sale__branch"
        ).order_by("-sale__created_at")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(sale__branch_id__in=accessible)
        return qs

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        payment = self.get_object()
        new_status = request.data.get("status")
        valid_statuses = [c[0] for c in Payment.RECONCILIATION_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({"detail": f"status must be one of {valid_statuses}"}, status=400)

        previous_status = payment.reconciliation_status
        payment.reconciliation_status = new_status
        payment.reconciliation_note = request.data.get("note", payment.reconciliation_note)
        if new_status in ("confirmed", "reconciled"):
            payment.reconciled_by = request.user
            payment.reconciled_at = timezone.now()
        payment.save(update_fields=["reconciliation_status", "reconciliation_note", "reconciled_by", "reconciled_at"])

        log_action(
            business=payment.business, actor=request.user, action="other", target=payment,
            branch=payment.sale.branch,
            previous_value={"reconciliation_status": previous_status},
            new_value={"reconciliation_status": new_status},
            reason=f"Payment reconciliation status changed to {new_status}.",
        )
        return Response(PaymentReconciliationListSerializer(payment).data)


class PaymentMethodViewSet(TenantScopedModelViewSet):
    """Owner-configurable payment methods (spec section 6). Business-
    wide, not per-branch — same reasoning as ExchangeRate: a payment
    method (Cash, Bank Transfer, Mobile Money...) is a business-level
    concept, not something that differs by location, so this
    deliberately isn't a BranchScopedModelViewSet and works the same
    for a main branch or any of its mini-branches.

    Any business member can read the list (a cashier needs it to
    sell); only an owner/admin can add, rename, reorder, or deactivate
    one — configuring how the business gets paid is a settings-level
    decision, not a day-to-day staff action."""
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsOwnerOrAdmin()]
        return [IsBusinessMember()]

    def get_queryset(self):
        business_id = self.request.business_id
        from apps.tenants.models import Business
        services.ensure_default_payment_methods(Business.objects.get(pk=business_id))
        return super().get_queryset()

    def perform_create(self, serializer):
        from django.utils.text import slugify
        name = serializer.validated_data.get("name", "")
        base_slug = slugify(name)[:25] or "method"
        code = base_slug
        n = 2
        while PaymentMethod.objects.filter(business_id=self.request.business_id, code=code).exists():
            code = f"{base_slug}-{n}"
            n += 1
        serializer.save(business_id=self.request.business_id, code=code)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.code == "cash":
            raise DRFValidationError("The Cash payment method can't be deleted.")
        if Payment.objects.filter(business_id=request.business_id, method=instance.code).exists():
            raise DRFValidationError("This method has payments recorded against it — deactivate it instead of deleting.")
        return super().destroy(request, *args, **kwargs)


class ExchangeRateViewSet(TenantScopedModelViewSet):
    """Manual FX rates the owner/admin keeps up to date — no live feed.
    Latest rate per currency is what the POS suggests as a default
    when a cashier records a foreign-currency payment (still editable
    per-payment on the Payment itself)."""
    queryset = ExchangeRate.objects.select_related("set_by").all()
    serializer_class = ExchangeRateSerializer
    filterset_fields = ["currency_code"]

    def get_permissions(self):
        # Cashiers need to read the current rate at POS, but setting
        # it is an owner/admin financial control — the docstring above
        # always said so, this just actually enforces it now.
        if self.request.method not in SAFE_METHODS:
            return [IsOwnerOrAdmin()]
        return [IsBusinessMember()]

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.business_id, set_by=self.request.user)

    @action(detail=False, methods=["get"])
    def latest(self, request):
        """One row per currency_code: the most recently set rate for
        each — what the POS actually needs, instead of the full history."""
        seen = set()
        latest = []
        for rate in self.get_queryset().order_by("currency_code", "-created_at"):
            if rate.currency_code in seen:
                continue
            seen.add(rate.currency_code)
            latest.append(rate)
        return Response(ExchangeRateSerializer(latest, many=True).data)
