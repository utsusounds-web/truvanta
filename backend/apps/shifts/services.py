from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.expenses.models import Expense, OwnerWithdrawal
from apps.notifications.services import notify
from apps.returns.models import SaleReturn
from apps.sales.models import Sale, Payment
from .models import Shift


def open_shift(*, business, branch, employee, opening_cash):
    # Scoped to the branch, not the employee — a branch has one shared
    # cash drawer. Allowing two employees to each hold an open shift on
    # the same branch meant POS sales (which always attach to whichever
    # shift opened most recently) would silently land on the wrong
    # person's shift, breaking their cash reconciliation with no
    # visible cause.
    existing = Shift.objects.filter(business=business, branch=branch, status="open").select_related("employee").first()
    if existing:
        who = existing.employee.get_full_name() or existing.employee.email
        raise ValidationError(f"There's already an open shift on this branch (opened by {who}). Close it first.")
    shift = Shift.objects.create(business=business, branch=branch, employee=employee, opening_cash=opening_cash)
    log_action(business=business, actor=employee, action="shift_event", target=shift, branch=branch,
               new_value={"opening_cash": str(opening_cash)}, reason="Shift opened.")
    return shift


def _compute_expected_cash(shift: Shift) -> Decimal:
    from django.db.models import Sum
    cash_sales = Payment.objects.filter(
        sale__shift=shift, method="cash", sale__status__in=["completed", "partially_refunded"],
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    cash_refunds = SaleReturn.objects.filter(
        sale__shift=shift, return_type="refund", status="approved",
    ).aggregate(total=Sum("refund_amount"))["total"] or Decimal("0")

    approved_expenses = Expense.objects.filter(
        branch=shift.branch, status="approved", created_at__gte=shift.opened_at,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    withdrawals = OwnerWithdrawal.objects.filter(
        branch=shift.branch, created_at__gte=shift.opened_at,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return shift.opening_cash + cash_sales - cash_refunds - approved_expenses - withdrawals


@transaction.atomic
def close_shift(*, shift: Shift, closing_physical_cash: Decimal, actor, variance_review_threshold=Decimal("1000")):
    """Blind-count close: the caller supplies the physically counted
    cash BEFORE this function computes/reveals the expected amount —
    the API layer must never send expected_closing_cash to the client
    ahead of this call. Classifies neutrally; never accuses anyone.
    """
    if shift.status != "open":
        raise ValidationError("Shift is not open.")

    expected = _compute_expected_cash(shift)
    variance = closing_physical_cash - expected

    if variance == 0:
        result = "balanced"
    elif abs(variance) > variance_review_threshold:
        result = "requires_review"
    elif variance > 0:
        result = "over"
    else:
        result = "short"

    shift.closing_physical_cash = closing_physical_cash
    shift.expected_closing_cash = expected
    shift.variance = variance
    shift.result = result
    shift.status = "pending_review" if result == "requires_review" else "reviewed"
    shift.closed_at = timezone.now()
    shift.save()

    log_action(
        business=shift.business, actor=actor, action="shift_event", target=shift, branch=shift.branch,
        new_value={"expected": str(expected), "physical": str(closing_physical_cash), "variance": str(variance), "result": result},
        reason="Shift closed.",
    )

    if result == "requires_review":
        notify(
            business=shift.business, branch=shift.branch, level="critical",
            title="Shift cash variance needs review",
            message=(
                f"{shift.employee.get_full_name() or shift.employee.email}'s shift at {shift.branch.name} "
                f"closed with a variance of {variance} (expected {expected}, counted {closing_physical_cash}). "
                f"This is flagged for review, not an accusation — take a look when you can."
            ),
            link_path="/shifts",
        )

    return shift
