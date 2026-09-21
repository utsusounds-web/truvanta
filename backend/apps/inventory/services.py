from django.db import transaction

from .models import StockMovement


@transaction.atomic
def record_movement(*, business, product, branch, quantity_delta, reason, performed_by=None,
                     reference_note="", source_type="", source_id="", client_reference=None):
    """The only sanctioned way to change stock. Every caller (sale
    posting, purchase receiving, returns, adjustments, transfers)
    should go through this so StockLevel is always derived from a
    real, attributed StockMovement row.

    If `client_reference` is given (a movement queued while offline)
    and one with that reference already exists for this business,
    the existing movement is returned unchanged rather than posting a
    duplicate — this is what makes a retried sync safe.
    """
    from django.core.exceptions import ValidationError

    if product.is_bundle:
        # This is the single choke point every stock change passes
        # through, so the bundle guard belongs here above anywhere
        # else — a caller-specific check (transfers, purchase orders)
        # only protects that one path; this protects all of them,
        # including ones written after this comment. A bundle
        # genuinely has no stock of its own (apps.sales.services
        # always resolves it to its components before ever calling
        # this), so a direct call reaching here is always a bug, not
        # a legitimate business action to allow through.
        raise ValidationError(f"'{product.name}' is a bundle and has no stock of its own — its components do.")

    if client_reference:
        existing = StockMovement.objects.filter(business=business, client_reference=client_reference).first()
        if existing:
            return existing

    return StockMovement.objects.create(
        business=business, product=product, branch=branch,
        quantity_delta=quantity_delta, reason=reason, performed_by=performed_by,
        reference_note=reference_note, source_type=source_type, source_id=source_id,
        client_reference=client_reference,
    )


@transaction.atomic
def send_transfer(*, business, product, from_branch, to_branch, quantity, sent_by, note=""):
    """Deducts stock from the sending branch immediately (it's
    physically left the shelf) and creates a pending StockTransfer.
    The receiving branch's stock only increases once they confirm
    receipt — see receive_transfer — so stock is never double-counted
    as being in two branches at once.
    """
    from django.core.exceptions import ValidationError
    from .models import StockTransfer

    if product.is_bundle:
        raise ValidationError("A bundle can't be transferred directly — transfer its component products instead.")

    transfer = StockTransfer.objects.create(
        business=business, product=product, from_branch=from_branch, to_branch=to_branch,
        quantity_sent=quantity, sent_by=sent_by, note=note,
    )
    record_movement(
        business=business, product=product, branch=from_branch, quantity_delta=-quantity,
        reason="branch_transfer_out", performed_by=sent_by,
        source_type="stock_transfer", source_id=str(transfer.id),
        reference_note=f"Transfer to {to_branch.name}",
    )
    return transfer


@transaction.atomic
def receive_transfer(*, transfer, quantity_received, received_by):
    """Confirms what actually arrived at the receiving branch. Only
    the confirmed quantity is added to stock — a shortfall is a
    visible discrepancy (status='received_with_discrepancy'), never
    silently reconciled to match what was sent.
    """
    from django.core.exceptions import ValidationError
    from django.utils import timezone

    if transfer.status != "pending":
        raise ValidationError("This transfer has already been received.")

    record_movement(
        business=transfer.business, product=transfer.product, branch=transfer.to_branch,
        quantity_delta=quantity_received, reason="branch_transfer_in", performed_by=received_by,
        source_type="stock_transfer", source_id=str(transfer.id),
        reference_note=f"Transfer from {transfer.from_branch.name}",
    )
    transfer.quantity_received = quantity_received
    transfer.status = "received" if quantity_received == transfer.quantity_sent else "received_with_discrepancy"
    transfer.received_by = received_by
    transfer.received_at = timezone.now()
    transfer.save(update_fields=["quantity_received", "status", "received_by", "received_at"])
    return transfer
