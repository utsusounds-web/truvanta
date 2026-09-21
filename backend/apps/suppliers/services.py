from django.db import transaction

from apps.audit.services import log_action
from apps.inventory.services import record_movement
from apps.ledger import services as ledger
from apps.products.models import ProductBatch
from .models import GoodsReceipt, GoodsReceiptItem, PurchaseOrder


def supplier_reliability_scorecard(*, business, supplier=None):
    """Supplier Reliability Scorecard (differentiator feature) — three
    plain, real metrics built entirely from purchase order and goods
    receipt data the business already has:

    - On-time %: of POs where a delivery date was actually promised
      (expected_delivery_date set) and later fully received, what
      share were received by that date. A PO with no promised date is
      excluded rather than guessed at — there's nothing to compare
      against.
    - Discrepancy rate: damaged + missing units as a percentage of
      units actually received, across every delivery from this
      supplier.
    - Price stability: of every time this supplier has been paid
      for the same product more than once, what share of those
      repeat purchases came in at a different unit cost than the
      previous one. Lower is more stable pricing.
    """
    from apps.suppliers.models import Supplier, PurchaseOrderItem

    suppliers = Supplier.objects.filter(business=business)
    if supplier:
        suppliers = suppliers.filter(pk=supplier.pk)

    rows = []
    for s in suppliers:
        pos = PurchaseOrder.objects.filter(supplier=s).exclude(status="cancelled")

        # On-time %
        dated_pos = pos.filter(expected_delivery_date__isnull=False, status="received")
        on_time_count = 0
        dated_count = 0
        for po in dated_pos:
            last_receipt = po.goods_receipts.order_by("-created_at").first()
            if not last_receipt:
                continue
            dated_count += 1
            if last_receipt.created_at.date() <= po.expected_delivery_date:
                on_time_count += 1
        on_time_percent = round((on_time_count / dated_count) * 100, 1) if dated_count else None

        # Discrepancy rate
        receipt_items = GoodsReceiptItem.objects.filter(goods_receipt__purchase_order__supplier=s)
        total_received = sum((i.quantity_received for i in receipt_items), 0)
        total_discrepant = sum((i.quantity_damaged + i.quantity_missing for i in receipt_items), 0)
        discrepancy_rate_percent = round((total_discrepant / total_received) * 100, 1) if total_received else None

        # Price stability — walk each product's purchase history from
        # this supplier in order, count how often the price changed
        # from the previous purchase of that same product.
        items = (
            PurchaseOrderItem.objects.filter(purchase_order__supplier=s)
            .select_related("product")
            .order_by("product_id", "purchase_order__created_at")
        )
        last_price_by_product = {}
        price_changes = 0
        repeat_purchases = 0
        for item in items:
            prev = last_price_by_product.get(item.product_id)
            if prev is not None:
                repeat_purchases += 1
                if prev != item.unit_cost:
                    price_changes += 1
            last_price_by_product[item.product_id] = item.unit_cost
        price_change_rate_percent = round((price_changes / repeat_purchases) * 100, 1) if repeat_purchases else None

        rows.append({
            "supplier_id": str(s.id),
            "supplier_name": s.name,
            "purchase_orders_count": pos.count(),
            "on_time_delivery_percent": on_time_percent,
            "on_time_sample_size": dated_count,
            "discrepancy_rate_percent": discrepancy_rate_percent,
            "price_change_rate_percent": price_change_rate_percent,
            "price_stability_sample_size": repeat_purchases,
        })

    rows.sort(key=lambda r: r["supplier_name"])
    return {"suppliers": rows}


@transaction.atomic
def receive_goods(*, purchase_order: PurchaseOrder, line_receipts, received_by, notes=""):
    """line_receipts: list of dicts {purchase_order_item, quantity_received, quantity_damaged,
    quantity_missing, batch_number (optional), expiry_date (optional)}.
    Posts a StockMovement (reason='purchase') for each accepted quantity in the
    product's base unit, flags discrepancies, and updates PO status.

    If the product has track_batches enabled and a batch_number was
    given for this line, also records a ProductBatch — this is the
    only place in the app batches ever get created, since a batch is
    fundamentally "however much of X arrived together, on this date,
    identified this way", which only makes sense at the point goods
    actually come in.
    """
    receipt = GoodsReceipt.objects.create(
        business=purchase_order.business, purchase_order=purchase_order, received_by=received_by, notes=notes,
    )
    fully_received = True
    received_value = 0
    for line in line_receipts:
        poi = line["purchase_order_item"]
        GoodsReceiptItem.objects.create(
            business=purchase_order.business, goods_receipt=receipt, purchase_order_item=poi,
            quantity_received=line["quantity_received"], quantity_damaged=line.get("quantity_damaged", 0),
            quantity_missing=line.get("quantity_missing", 0),
        )
        if line["quantity_received"] > 0:
            # Convert from the PO's unit into the product's base unit.
            conversion = poi.product.units.filter(unit=poi.unit).first()
            factor = conversion.conversion_factor_to_base if conversion else 1
            base_unit_quantity = line["quantity_received"] * factor
            record_movement(
                business=purchase_order.business, product=poi.product, branch=purchase_order.branch,
                quantity_delta=base_unit_quantity, reason="purchase", performed_by=received_by,
                source_type="purchase_order", source_id=str(purchase_order.id),
                reference_note=f"Received against PO {purchase_order.reference_number}",
            )
            received_value += line["quantity_received"] * poi.unit_cost

            if poi.product.track_batches and line.get("batch_number"):
                batch, created = ProductBatch.objects.get_or_create(
                    business=purchase_order.business, product=poi.product, branch=purchase_order.branch,
                    batch_number=line["batch_number"],
                    defaults={
                        "quantity_received": base_unit_quantity,
                        "expiry_date": line.get("expiry_date") if poi.product.track_expiry else None,
                    },
                )
                if not created:
                    # Same batch number received again (a second delivery
                    # against the same batch) — add to it rather than
                    # silently overwrite, so nothing already counted is lost.
                    batch.quantity_received += base_unit_quantity
                    batch.save(update_fields=["quantity_received"])
        if line.get("quantity_missing") or line.get("quantity_damaged"):
            log_action(
                business=purchase_order.business, actor=received_by, action="other", target=receipt,
                branch=purchase_order.branch,
                new_value={
                    "purchase_order_item": str(poi.id),
                    "product": poi.product.name,
                    "quantity_received": str(line.get("quantity_received", 0)),
                    "quantity_damaged": str(line.get("quantity_damaged", 0)),
                    "quantity_missing": str(line.get("quantity_missing", 0)),
                },
                reason="Discrepancy on goods receipt (missing/damaged).",
            )
        if line["quantity_received"] < poi.quantity_ordered:
            fully_received = False

    purchase_order.status = "received" if fully_received else "partially_received"
    purchase_order.save(update_fields=["status"])

    if received_value > 0:
        ledger.post_entry(
            business=purchase_order.business, branch=purchase_order.branch,
            description=f"Goods received against PO {purchase_order.reference_number}",
            lines=[(ledger.INVENTORY, received_value, 0), (ledger.ACCOUNTS_PAYABLE, 0, received_value)],
            source_type="goods_receipt", source_id=str(receipt.id), created_by=received_by,
        )

    return receipt
