from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse

from apps.billing.permissions import HasFeature
from apps.core.viewsets import TenantScopedModelViewSet, BranchScopedModelViewSet
from apps.core.permissions import IsBusinessMember, HasBusinessPermission
from .models import Supplier, SupplierLedgerEntry, PurchaseOrder, PurchaseOrderItem, GoodsReceipt
from .serializers import (
    SupplierSerializer, SupplierLedgerEntrySerializer, PurchaseOrderSerializer,
    PurchaseOrderItemSerializer, GoodsReceiptSerializer,
)
from . import services


class RequireManageSuppliers(HasBusinessPermission):
    required_permission_code = "manage_suppliers"


class SupplierViewSet(TenantScopedModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["name", "phone_number"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "statement_pdf"):
            return [IsBusinessMember()]
        return [RequireManageSuppliers()]

    @action(detail=True, methods=["get"], url_path="statement-pdf")
    def statement_pdf(self, request, pk=None):
        from .documents import generate_supplier_statement_pdf
        supplier = self.get_object()
        entries = supplier.ledger_entries.order_by("created_at")
        pdf_bytes = generate_supplier_statement_pdf(supplier, entries)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{supplier.name}-statement.pdf"'
        return response

    @action(detail=False, methods=["get"], url_path="reliability-scorecard")
    def reliability_scorecard(self, request):
        from apps.tenants.models import Business
        business = Business.objects.get(pk=request.business_id)
        data = services.supplier_reliability_scorecard(business=business)
        return Response(data)


class SupplierLedgerEntryViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = SupplierLedgerEntry.objects.all()
    serializer_class = SupplierLedgerEntrySerializer
    filterset_fields = ["supplier", "entry_type"]

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.business_id, recorded_by=self.request.user)


class RequirePurchaseOrders(HasFeature):
    required_feature_key = "purchase_orders"


class PurchaseOrderViewSet(BranchScopedModelViewSet):
    queryset = PurchaseOrder.objects.prefetch_related("items")
    serializer_class = PurchaseOrderSerializer
    filterset_fields = ["supplier", "branch", "status"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [RequirePurchaseOrders()]
        return [RequirePurchaseOrders(), RequireManageSuppliers()]

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        self._check_branch_access(branch)
        serializer.save(business_id=self.request.business_id, created_by=self.request.user)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        from .documents import generate_purchase_order_pdf
        po = self.get_object()
        pdf_bytes = generate_purchase_order_pdf(po)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{po.reference_number}.pdf"'
        return response

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        po = self.get_object()
        line_receipts = []
        for line in request.data.get("items", []):
            poi = PurchaseOrderItem.objects.get(pk=line["purchase_order_item"], business_id=request.business_id)
            line_receipts.append({
                "purchase_order_item": poi,
                "quantity_received": line.get("quantity_received", 0),
                "quantity_damaged": line.get("quantity_damaged", 0),
                "quantity_missing": line.get("quantity_missing", 0),
                "batch_number": line.get("batch_number", ""),
                "expiry_date": line.get("expiry_date") or None,
            })
        receipt = services.receive_goods(purchase_order=po, line_receipts=line_receipts, received_by=request.user)
        return Response(GoodsReceiptSerializer(receipt).data, status=201)


class PurchaseOrderItemViewSet(TenantScopedModelViewSet):
    permission_classes = [RequirePurchaseOrders]
    queryset = PurchaseOrderItem.objects.all()
    serializer_class = PurchaseOrderItemSerializer
    filterset_fields = ["purchase_order"]

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(purchase_order__branch_id__in=accessible)
        return qs


class GoodsReceiptViewSet(TenantScopedModelViewSet):
    permission_classes = [RequirePurchaseOrders]
    http_method_names = ["get", "head", "options"]
    queryset = GoodsReceipt.objects.prefetch_related("items")
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(purchase_order__branch_id__in=accessible)
        return qs

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        from .documents import generate_goods_receipt_pdf
        receipt = self.get_object()
        pdf_bytes = generate_goods_receipt_pdf(receipt)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="goods-receipt-{receipt.purchase_order.reference_number}.pdf"'
        return response
