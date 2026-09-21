from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import log_action
from apps.customers.models import CustomerCreditTransaction
from apps.inventory.services import record_movement
from apps.notifications.services import notify
from apps.products.services import stock_deductions_for
from apps.sales.models import Payment
from .models import SaleReturn


def notify_if_large_refund_while_away(sale_return: SaleReturn):
    """Called when a refund is first requested (not when approved) —
    the point of away mode is the owner finding out immediately that
    something needs their attention, not after it's already resolved.
    Refunds require approval regardless of this setting; this only
    controls whether it's flagged as urgent right away.
    """
    business = sale_return.business
    threshold = business.away_mode_refund_threshold_amount
    if (
        business.away_mode_enabled and threshold
        and sale_return.return_type == "refund" and sale_return.refund_amount > threshold
    ):
        notify(
            business=business, level="critical",
            title="Large refund requested while you're away",
            message=f"A refund of {sale_return.refund_amount} was requested on {sale_return.sale.transaction_number} "
                    f"— above your {threshold} away-mode limit. It's waiting for your approval.",
            link_path="/returns",
        )


@transaction.atomic
def approve_return(*, sale_return: SaleReturn, actor):
    if sale_return.status != "pending_approval":
        raise ValidationError("Return is not pending approval.")

    if sale_return.restock:
        # Same rule as selling: a bundle has no stock of its own, so
        # returning one restocks its components, in the same
        # proportions it originally deducted them in — never the
        # bundle's own (nonexistent) stock.
        for stock_product, stock_qty in stock_deductions_for(sale_return.sale_item.product, sale_return.quantity):
            record_movement(
                business=sale_return.business, product=stock_product, branch=sale_return.sale.branch,
                quantity_delta=stock_qty, reason="customer_return", performed_by=actor,
                source_type="sale_return", source_id=str(sale_return.id),
            )

    if sale_return.return_type == "refund" and sale_return.refund_amount > 0:
        sale = sale_return.sale
        if sale.sale_type == "credit" and sale.customer:
            CustomerCreditTransaction.objects.create(
                business=sale_return.business, customer=sale.customer, entry_type="adjustment",
                amount=-sale_return.refund_amount, source_type="sale_return", source_id=str(sale_return.id),
                recorded_by=actor, reference_note=f"Refund for return on {sale.transaction_number}",
            )
        # Cash/other refunds reduce cash on hand for shift reconciliation via
        # apps.shifts.services._compute_expected_cash, which reads approved refunds directly.

    sale_return.status = "approved"
    sale_return.approved_by = actor
    sale_return.save(update_fields=["status", "approved_by"])

    log_action(
        business=sale_return.business, actor=actor, action="return", target=sale_return,
        new_value={"status": "approved", "quantity": str(sale_return.quantity)}, reason=sale_return.reason,
    )
    return sale_return
