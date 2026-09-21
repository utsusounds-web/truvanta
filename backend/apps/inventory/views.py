from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.viewsets import TenantScopedModelViewSet, BranchScopedModelViewSet
from apps.core.permissions import HasBusinessPermission
from apps.audit.services import log_action
from .models import StockLevel, StockMovement, StockTransfer
from .serializers import StockLevelSerializer, StockMovementSerializer, StockTransferSerializer
from . import services


class RequireManageInventory(HasBusinessPermission):
    required_permission_code = "manage_inventory"


class StockLevelViewSet(BranchScopedModelViewSet):
    http_method_names = ["get", "head", "options"]  # read-only: change stock via movements only
    queryset = StockLevel.objects.select_related("product", "branch")
    serializer_class = StockLevelSerializer
    filterset_fields = ["branch", "product"]


class StockMovementViewSet(BranchScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]  # append-only
    queryset = StockMovement.objects.select_related("product", "branch")
    serializer_class = StockMovementSerializer
    filterset_fields = ["branch", "product", "reason"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [RequireManageInventory()]

    def create(self, request, *args, **kwargs):
        # Manual adjustments only — sales/purchases/returns post movements
        # via their own service functions, not this generic endpoint.
        if request.data.get("reason") not in ("adjustment", "opening_stock", "damage", "expiry", "personal_use", "other"):
            raise PermissionDenied("This reason must be posted via its owning workflow (sale, purchase, return, transfer).")

        accessible = request.accessible_branch_ids
        if accessible is not None and str(request.data.get("branch")) not in {str(b) for b in accessible}:
            raise PermissionDenied("You don't have access to that branch.")

        client_reference = request.data.get("client_reference") or None
        if client_reference:
            existing = StockMovement.objects.filter(business_id=request.business_id, client_reference=client_reference).first()
            if existing:
                return Response(self.get_serializer(existing).data, status=200)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = serializer.save(business_id=self.request.business_id, performed_by=self.request.user)
        # Manual stock changes (adjustment/damage/expiry/personal_use/
        # opening_stock/other) are exactly the kind most worth having a
        # record of — e.g. "damage" written off can otherwise be a
        # cover story for shrinkage/theft with no trace of who did it
        # or when. Sale/purchase/return-driven movements are logged by
        # their own owning workflow instead (see the reason check above).
        log_action(
            business=movement.business, actor=request.user, action="stock_adjustment",
            target=movement, branch=movement.branch,
            new_value={
                "product": movement.product.name,
                "quantity_delta": str(movement.quantity_delta),
                "reason": movement.get_reason_display(),
            },
            reason=movement.reference_note,
        )
        return Response(serializer.data, status=201)


class StockTransferViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = StockTransfer.objects.select_related("product", "from_branch", "to_branch")
    serializer_class = StockTransferSerializer
    filterset_fields = ["from_branch", "to_branch", "status", "product"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [RequireManageInventory()]

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            from django.db.models import Q
            qs = qs.filter(Q(from_branch_id__in=accessible) | Q(to_branch_id__in=accessible))
        return qs

    def create(self, request, *args, **kwargs):
        product_id = request.data.get("product")
        from_branch_id = request.data.get("from_branch")
        to_branch_id = request.data.get("to_branch")
        quantity = request.data.get("quantity_sent")
        note = request.data.get("note", "")

        from apps.products.models import Product
        from apps.tenants.models import Branch

        product = Product.objects.get(pk=product_id, business_id=request.business_id)
        from_branch = Branch.objects.get(pk=from_branch_id, business_id=request.business_id)
        to_branch = Branch.objects.get(pk=to_branch_id, business_id=request.business_id)

        accessible = request.accessible_branch_ids
        if accessible is not None and from_branch.id not in accessible:
            raise PermissionDenied("You don't have access to the sending branch.")

        try:
            transfer = services.send_transfer(
                business=product.business, product=product, from_branch=from_branch,
                to_branch=to_branch, quantity=quantity, sent_by=request.user, note=note,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        return Response(StockTransferSerializer(transfer).data, status=201)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        transfer = self.get_object()
        accessible = request.accessible_branch_ids
        if accessible is not None and transfer.to_branch_id not in accessible:
            raise PermissionDenied("You don't have access to the receiving branch.")
        quantity_received = request.data.get("quantity_received")
        updated = services.receive_transfer(
            transfer=transfer, quantity_received=quantity_received, received_by=request.user,
        )
        return Response(StockTransferSerializer(updated).data)
