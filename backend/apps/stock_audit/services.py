import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.inventory.models import StockLevel
from .models import QuickAudit, QuickAuditLine


@transaction.atomic
def trigger_quick_audit(*, business, branch, triggered_by, sample_size=5):
    """Randomly selects products to spot-check, weighted toward
    higher-value stock (a discrepancy there costs more) so the sample
    isn't wasted on low-value items, while still leaving room for
    pure random picks so it can't be gamed by knowing what's excluded.
    """
    levels = list(StockLevel.objects.filter(business=business, branch=branch, quantity__gt=0).select_related("product"))
    if not levels:
        raise ValidationError(
            "There's no stock recorded at this branch yet — having products in your catalog isn't "
            "the same as having quantity on hand recorded for them here. Go to Inventory → Record "
            "movement → Stock Purchase to add your opening stock for this branch first, then come back "
            "to run an audit."
        )

    weighted = sorted(levels, key=lambda l: l.quantity * l.product.cost_price, reverse=True)
    high_value_pool = weighted[: max(sample_size, len(weighted) // 2)]
    sample_count = min(sample_size, len(levels))
    chosen = random.sample(high_value_pool, min(sample_count, len(high_value_pool)))
    if len(chosen) < sample_count:
        remaining = [l for l in levels if l not in chosen]
        chosen += random.sample(remaining, min(sample_count - len(chosen), len(remaining)))

    audit = QuickAudit.objects.create(business=business, branch=branch, triggered_by=triggered_by)
    for level in chosen:
        QuickAuditLine.objects.create(
            business=business, audit=audit, product=level.product, expected_quantity=level.quantity,
        )

    log_action(
        business=business, actor=triggered_by, action="stock_adjustment", target=audit, branch=branch,
        new_value={"product_count": len(chosen)}, reason="Quick random stock audit triggered.",
    )
    return audit


@transaction.atomic
def record_counts(*, audit: QuickAudit, counts: dict, counted_by):
    """counts: {audit_line_id: physical_quantity}. Saves each count
    and, once every line has one, marks the audit completed. Never
    touches StockLevel — this is a verification record, not a stock
    adjustment; the owner decides what (if anything) to do about a
    discrepancy via a normal stock adjustment afterward.
    """
    if audit.status == "completed":
        raise ValidationError("This audit is already completed.")

    lines = {str(l.id): l for l in audit.lines.all()}
    for line_id, physical_qty in counts.items():
        line = lines.get(str(line_id))
        if not line:
            continue
        line.physical_quantity = Decimal(str(physical_qty))
        line.counted_by = counted_by
        line.counted_at = timezone.now()
        line.save(update_fields=["physical_quantity", "counted_by", "counted_at"])

    audit.refresh_from_db()
    if all(l.physical_quantity is not None for l in audit.lines.all()):
        audit.status = "completed"
        audit.completed_at = timezone.now()
        audit.save(update_fields=["status", "completed_at"])
        discrepant = [l for l in audit.lines.all() if l.difference != 0]
        log_action(
            business=audit.business, actor=counted_by, action="stock_adjustment", target=audit, branch=audit.branch,
            new_value={"discrepant_count": len(discrepant)}, reason="Quick audit completed.",
        )
    return audit
