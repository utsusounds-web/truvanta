from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.sales.services import create_sale


@transaction.atomic
def convert_to_sale(*, quotation, cashier, payments, sale_type="cash", shift=None):
    """Turns an accepted quotation into a real Sale — this is the
    only point a quotation ever touches inventory or the ledger.
    Delegates entirely to sales.services.create_sale so a converted
    quotation is indistinguishable from a sale rung up directly at
    the till: same stock deduction, same audit trail, same
    everything. The quotation itself just gets marked 'converted' and
    linked to the resulting sale — it's never deleted, so the
    original quote is still on record for reference.
    """
    if quotation.status not in ("draft", "sent", "accepted"):
        raise ValidationError(f"A {quotation.get_status_display().lower()} quotation can't be converted.")
    if quotation.valid_until and quotation.valid_until < timezone.now().date():
        raise ValidationError("This quotation has expired and can't be converted as-is — issue a new one.")
    if not quotation.items.exists():
        raise ValidationError("This quotation has no line items.")

    items = [
        {
            "product": item.product, "unit": item.unit, "quantity": item.quantity,
            "unit_price": item.unit_price, "discount_amount": item.discount_amount,
        }
        for item in quotation.items.select_related("product", "unit")
    ]

    sale = create_sale(
        business=quotation.business, branch=quotation.branch, cashier=cashier,
        items=items, payments=payments, customer=quotation.customer, sale_type=sale_type, shift=shift,
        note=f"Converted from {quotation.get_document_type_display()} {quotation.reference_number}",
    )

    quotation.status = "converted"
    quotation.converted_sale = sale
    quotation.save(update_fields=["status", "converted_sale"])

    log_action(
        business=quotation.business, actor=cashier, action="other", target=quotation,
        new_value={"status": "converted", "sale": str(sale.id)},
        reason=f"Converted {quotation.get_document_type_display().lower()} to a sale",
    )
    return sale


def mark_expired_quotations(business):
    """Run periodically (or lazily on list/read — see views) to flip
    anything past its valid_until into 'expired' so the status shown
    is never stale. Never touches anything already accepted/converted/void."""
    from .models import Quotation
    Quotation.objects.filter(
        business=business, status__in=["draft", "sent"], valid_until__lt=timezone.now().date(),
    ).update(status="expired")
