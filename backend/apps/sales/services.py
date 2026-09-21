from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import log_action
from apps.customers.models import CustomerCreditTransaction
from apps.inventory.models import StockLevel
from apps.inventory.services import record_movement
from apps.ledger import services as ledger
from apps.ledger.models import JournalEntry as LedgerJournalEntry
from apps.notifications.services import notify
from apps.products.services import stock_deductions_for
from .models import Sale, SaleItem, Payment, ReceiptPrintLog, PaymentMethod


DEFAULT_PAYMENT_METHODS = [
    ("cash", "Cash", 0),
    ("bank_transfer", "Bank Transfer", 1),
    ("card", "POS / Card", 2),
    ("other", "Other", 3),
]


def ensure_default_payment_methods(business):
    """Seeds the four methods that used to be hardcoded, the first
    time a business's payment methods are ever looked at — so an
    existing business gets exactly the options it already had, and a
    new one starts with a sensible baseline it can then customize."""
    if PaymentMethod.objects.filter(business=business).exists():
        return
    for code, name, order in DEFAULT_PAYMENT_METHODS:
        PaymentMethod.objects.get_or_create(business=business, code=code, defaults={"name": name, "sort_order": order})


@transaction.atomic
def create_sale(*, business, branch, cashier, items, payments, customer=None,
                 sale_type="cash", shift=None, note="", tax_total=Decimal("0"), client_reference=None):
    """Post a complete sale: create Sale + SaleItems, deduct inventory
    (one StockMovement per line, reason='sale'), record Payments,
    post a credit-ledger entry for credit sales, and write an audit
    record for the sale plus one per discounted line. This is the
    only place a Sale should be created from — it's what keeps
    inventory, cash, and the audit trail consistent with each sale.

    If `client_reference` is given (an offline-queued sale being
    synced) and a sale with that reference already exists for this
    business, that existing sale is returned unchanged instead of
    posting a duplicate — this is what makes a retried sync safe.

    `items`: list of dicts: product, unit, quantity, unit_price, discount_amount
    `payments`: list of dicts: method, amount, reference
    """
    if client_reference:
        existing = Sale.objects.filter(business=business, client_reference=client_reference).first()
        if existing:
            return existing

    if not items:
        raise ValidationError("A sale must have at least one item.")

    # This is the single place a Sale is ever created (see docstring),
    # so payment-method validation belongs here rather than
    # duplicated in every caller — a caller that validated this itself
    # and one that forgot would otherwise behave differently for the
    # exact same bad input.
    ensure_default_payment_methods(business)
    active_codes = set(PaymentMethod.objects.filter(business=business, is_active=True).values_list("code", flat=True))
    for p in payments:
        if p["method"] not in active_codes:
            raise ValidationError(f"'{p['method']}' isn't a configured payment method for this business.")

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    total_cogs = Decimal("0")
    sale = Sale.objects.create(
        business=business, branch=branch, cashier=cashier, shift=shift, customer=customer,
        sale_type=sale_type, note=note, tax_total=tax_total, client_reference=client_reference,
    )

    for item in items:
        quantity = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["unit_price"]))
        discount_amount = Decimal(str(item.get("discount_amount", 0)))
        line_total = (quantity * unit_price) - discount_amount

        SaleItem.objects.create(
            business=business, sale=sale, product=item["product"], unit=item["unit"],
            quantity=quantity, unit_price=unit_price, discount_amount=discount_amount, line_total=line_total,
        )
        subtotal += quantity * unit_price
        discount_total += discount_amount

        # A bundle has no stock of its own — stock_deductions_for
        # resolves to its components instead (see products.services
        # docstring). An ordinary product or variant resolves to just
        # itself. Computed once and reused for both COGS (must reflect
        # what actually left inventory, not the sold product's own
        # cost_price — for a bundle those are different things) and
        # the actual stock movements.
        deductions = stock_deductions_for(item["product"], quantity)
        for stock_product, stock_qty in deductions:
            total_cogs += stock_qty * stock_product.cost_price

        for stock_product, stock_qty in deductions:
            record_movement(
                business=business, product=stock_product, branch=branch,
                quantity_delta=-stock_qty, reason="sale", performed_by=cashier,
                source_type="sale", source_id=str(sale.id),
            )
            reorder_level = stock_product.reorder_level
            if reorder_level and reorder_level > 0:
                level = StockLevel.objects.filter(business=business, product=stock_product, branch=branch).first()
                if level and level.quantity <= reorder_level:
                    notify(
                        business=business, branch=branch, level="important",
                        title=f"Low stock: {stock_product.name}",
                        message=f"{stock_product.name} is down to {level.quantity} at {branch.name} "
                                f"(reorder level is {reorder_level}). Time to restock.",
                        link_path="/inventory",
                    )

        if discount_amount > 0:
            log_action(
                business=business, actor=cashier, action="discount", target=sale, branch=branch,
                new_value={"product": str(item["product"]), "discount_amount": str(discount_amount)},
                reason="Discount applied on sale line.",
            )
            threshold = business.away_mode_discount_threshold_percent
            line_value = quantity * unit_price
            if business.away_mode_enabled and threshold and line_value > 0:
                discount_percent = (discount_amount / line_value) * 100
                if discount_percent > threshold:
                    notify(
                        business=business, branch=branch, level="critical",
                        title=f"Large discount while you're away: {item['product'].name}",
                        message=f"A {discount_percent:.1f}% discount was given on {item['product'].name} "
                                f"({discount_amount} off {line_value}) — above your {threshold}% away-mode limit.",
                        link_path="/activity-log",
                    )

    sale.subtotal = subtotal
    sale.discount_total = discount_total
    sale.grand_total = subtotal - discount_total + tax_total
    sale.save(update_fields=["subtotal", "discount_total", "grand_total"])

    paid_total = Decimal("0")
    for p in payments:
        foreign_code = p.get("foreign_currency_code", "")
        foreign_amount = p.get("foreign_amount")
        exchange_rate = p.get("exchange_rate")
        if foreign_code and foreign_amount is not None:
            amount = (Decimal(str(foreign_amount)) * Decimal(str(exchange_rate))).quantize(Decimal("0.01"))
        else:
            amount = Decimal(str(p["amount"]))
        Payment.objects.create(
            business=business, sale=sale, method=p["method"], amount=amount, reference=p.get("reference", ""),
            foreign_currency_code=foreign_code, foreign_amount=foreign_amount, exchange_rate_used=exchange_rate,
        )
        paid_total += amount

    if sale_type == "credit":
        owed = sale.grand_total - paid_total
        if owed > 0:
            if customer is None:
                raise ValidationError("A customer is required for a credit sale.")
            CustomerCreditTransaction.objects.create(
                business=business, customer=customer, entry_type="credit_sale", amount=owed,
                source_type="sale", source_id=str(sale.id), recorded_by=cashier,
                reference_note=f"Credit sale {sale.transaction_number}",
            )

    ReceiptPrintLog.objects.create(business=business, sale=sale, printed_by=cashier, copy_number=1)

    # --- Double-entry ledger ---------------------------------------
    # Two balanced entries: (1) the sale itself — cash/bank/receivable
    # in, revenue and tax owed out; (2) moving the goods sold out of
    # Inventory into Cost of Goods Sold. Kept separate because they're
    # conceptually different events, even though both post atomically
    # here — this mirrors how a real set of books records a sale.
    revenue_lines = []
    cash_total = sum((p.amount for p in Payment.objects.filter(sale=sale) if p.method == "cash"), Decimal("0"))
    bank_total = sum((p.amount for p in Payment.objects.filter(sale=sale) if p.method in ("bank_transfer", "card")), Decimal("0"))
    other_total = sum((p.amount for p in Payment.objects.filter(sale=sale) if p.method == "other"), Decimal("0"))
    receivable = sale.grand_total - paid_total  # unpaid portion of a credit sale

    if cash_total:
        revenue_lines.append((ledger.CASH, cash_total, 0))
    if bank_total:
        revenue_lines.append((ledger.BANK, bank_total, 0))
    if other_total:
        revenue_lines.append((ledger.CASH, other_total, 0))
    if receivable > 0:
        revenue_lines.append((ledger.ACCOUNTS_RECEIVABLE, receivable, 0))
    revenue_lines.append((ledger.SALES_REVENUE, 0, subtotal - discount_total))
    if tax_total:
        revenue_lines.append((ledger.TAX_PAYABLE, 0, tax_total))

    ledger.post_entry(
        business=business, branch=branch, entry_date=sale.created_at,
        description=f"Sale {sale.transaction_number}", lines=revenue_lines,
        source_type="sale", source_id=str(sale.id), created_by=cashier,
    )
    if total_cogs > 0:
        ledger.post_entry(
            business=business, branch=branch, entry_date=sale.created_at,
            description=f"Cost of goods sold — {sale.transaction_number}",
            lines=[(ledger.COGS, total_cogs, 0), (ledger.INVENTORY, 0, total_cogs)],
            source_type="sale_cogs", source_id=str(sale.id), created_by=cashier,
        )

    log_action(
        business=business, actor=cashier, action="create", target=sale, branch=branch,
        new_value={"transaction_number": sale.transaction_number, "grand_total": str(sale.grand_total)},
        reason="Sale completed.",
    )
    return sale


@transaction.atomic
def cancel_sale(*, sale, actor, reason):
    """Controlled cancellation: reverses inventory for every line and
    marks the sale cancelled. The original Sale/SaleItem rows are
    never deleted — this is a documented reversal, not a rewrite of
    history."""
    if sale.status != "completed":
        raise ValidationError("Only a completed sale can be cancelled.")
    for item in sale.items.all():
        # Same rule as selling and returning: a bundle has no stock of
        # its own, so cancelling a sale that included one reverses its
        # components, not the bundle itself.
        for stock_product, stock_qty in stock_deductions_for(item.product, item.quantity):
            record_movement(
                business=sale.business, product=stock_product, branch=sale.branch,
                quantity_delta=stock_qty, reason="customer_return", performed_by=actor,
                source_type="sale_cancellation", source_id=str(sale.id),
                reference_note=f"Reversal for cancelled sale {sale.transaction_number}",
            )
    previous_status = sale.status
    sale.status = "cancelled"
    sale.save(update_fields=["status"])

    for entry in LedgerJournalEntry.objects.filter(business=sale.business, source_type__in=["sale", "sale_cogs"], source_id=str(sale.id)):
        ledger.reverse_entry(original=entry, description=f"Cancellation of sale {sale.transaction_number}: {reason}", created_by=actor)

    log_action(
        business=sale.business, actor=actor, action="cancellation", target=sale, branch=sale.branch,
        previous_value={"status": previous_status}, new_value={"status": "cancelled"}, reason=reason,
    )
    return sale


def reprint_receipt(*, sale, actor):
    last = sale.print_logs.order_by("-copy_number").first()
    copy_number = (last.copy_number + 1) if last else 1
    log = ReceiptPrintLog.objects.create(business=sale.business, sale=sale, printed_by=actor, copy_number=copy_number)
    log_action(
        business=sale.business, actor=actor, action="receipt_reprint", target=sale,
        new_value={"copy_number": copy_number}, reason="Receipt reprinted.",
    )
    return log
