from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.core.viewsets import TenantScopedModelViewSet, BranchScopedModelViewSet
from apps.core.permissions import HasBusinessPermission
from apps.ledger import services as ledger
from apps.ledger.models import JournalEntry as LedgerJournalEntry
from .models import ExpenseCategory, Expense, OwnerWithdrawal
from .serializers import ExpenseCategorySerializer, ExpenseSerializer, OwnerWithdrawalSerializer


class RequireApproveExpenses(HasBusinessPermission):
    required_permission_code = "approve_expenses"


class ExpenseCategoryViewSet(TenantScopedModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer


class ExpenseViewSet(BranchScopedModelViewSet):
    # No patch/put/delete: a posted expense is never silently edited or
    # removed — the void action below is the only way to reverse one,
    # and it's tracked in the audit log like every other correction.
    http_method_names = ["get", "post", "head", "options"]
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["branch", "category", "status"]

    def create(self, request, *args, **kwargs):
        accessible = request.accessible_branch_ids
        if accessible is not None and str(request.data.get("branch")) not in {str(b) for b in accessible}:
            raise PermissionDenied("You don't have access to that branch.")

        client_reference = request.data.get("client_reference") or None
        if client_reference:
            existing = Expense.objects.filter(business_id=request.business_id, client_reference=client_reference).first()
            if existing:
                return Response(self.get_serializer(existing).data, status=200)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(business_id=self.request.business_id, requested_by=self.request.user)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], permission_classes=[RequireApproveExpenses])
    def approve(self, request, pk=None):
        expense = self.get_object()
        expense.status = "approved"
        expense.approved_by = request.user
        expense.save(update_fields=["status", "approved_by"])
        ledger.post_entry(
            business=expense.business, branch=expense.branch, entry_date=expense.created_at,
            description=f"Expense: {expense.reason or expense.category.name}",
            lines=[(ledger.OPERATING_EXPENSES, expense.amount, 0), (ledger.CASH, 0, expense.amount)],
            source_type="expense", source_id=str(expense.id), created_by=request.user,
        )
        log_action(business=expense.business, actor=request.user, action="expense_change", target=expense,
                   branch=expense.branch, new_value={"status": "approved"}, reason="Expense approved.")
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"], permission_classes=[RequireApproveExpenses])
    def reject(self, request, pk=None):
        expense = self.get_object()
        expense.status = "rejected"
        expense.approved_by = request.user
        expense.save(update_fields=["status", "approved_by"])
        log_action(business=expense.business, actor=request.user, action="expense_change", target=expense,
                   branch=expense.branch, new_value={"status": "rejected"}, reason=request.data.get("reason", ""))
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """The only way to reverse a wrongly-entered expense — never a
        raw delete. Requires a reason, and it's logged like every other
        correction, so 'why is this ₦0 now' always has an answer."""
        expense = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"detail": "A reason is required to void an expense."}, status=400)
        previous_status = expense.status
        expense.status = "voided"
        expense.save(update_fields=["status"])
        for entry in LedgerJournalEntry.objects.filter(business=expense.business, source_type="expense", source_id=str(expense.id)):
            ledger.reverse_entry(original=entry, description=f"Void of expense: {reason}", created_by=request.user)
        log_action(business=expense.business, actor=request.user, action="expense_change", target=expense,
                   branch=expense.branch, previous_value={"status": previous_status},
                   new_value={"status": "voided"}, reason=reason)
        return Response(ExpenseSerializer(expense).data)


class OwnerWithdrawalViewSet(BranchScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = OwnerWithdrawal.objects.all()
    serializer_class = OwnerWithdrawalSerializer

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        self._check_branch_access(branch)
        withdrawal = serializer.save(business_id=self.request.business_id, withdrawn_by=self.request.user)
        ledger.post_entry(
            business=withdrawal.business, branch=withdrawal.branch, entry_date=withdrawal.created_at,
            description=f"Owner withdrawal: {withdrawal.note or 'personal use'}",
            lines=[(ledger.OWNERS_DRAWINGS, withdrawal.amount, 0), (ledger.CASH, 0, withdrawal.amount)],
            source_type="owner_withdrawal", source_id=str(withdrawal.id), created_by=self.request.user,
        )
