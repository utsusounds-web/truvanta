from decimal import Decimal

from django.db.models import Sum, Count, Max
from django.utils import timezone

from apps.sales.models import Sale
from apps.inventory.models import StockLevel
from apps.customers.models import Customer, CustomerCreditTransaction
from apps.audit.models import AuditLog


def owner_dashboard(*, business, branch=None, date_from=None, date_to=None):
    """Answers the five questions the spec calls out as the owner
    dashboard's job: what did I sell, what should I have, what stock
    do I have, who owes me, is there anything to investigate."""
    sales_qs = Sale.objects.filter(business=business, status__in=["completed", "partially_refunded"])
    if branch:
        sales_qs = sales_qs.filter(branch=branch)
    if date_from:
        sales_qs = sales_qs.filter(created_at__gte=date_from)
    if date_to:
        sales_qs = sales_qs.filter(created_at__lte=date_to)

    totals = sales_qs.aggregate(
        total_sales=Sum("grand_total"), total_discount=Sum("discount_total"), count=Count("id"),
    )

    stock_qs = StockLevel.objects.filter(business=business)
    if branch:
        stock_qs = stock_qs.filter(branch=branch)
    low_stock_count = sum(
        1 for level in stock_qs.select_related("product")
        if level.product.reorder_level and level.quantity <= level.product.reorder_level
    )

    debt_total = CustomerCreditTransaction.objects.filter(business=business).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    recent_alerts = AuditLog.objects.filter(
        business=business, action__in=["discount", "refund", "cancellation", "stock_adjustment", "receipt_reprint"],
    ).order_by("-created_at")[:20]

    return {
        "total_sales": totals["total_sales"] or Decimal("0"),
        "total_discount_given": totals["total_discount"] or Decimal("0"),
        "number_of_sales": totals["count"] or 0,
        "low_stock_product_count": low_stock_count,
        "total_customer_debt": debt_total,
        "items_to_investigate": [
            {"action": a.action, "reason": a.reason, "created_at": a.created_at.isoformat()}
            for a in recent_alerts
        ],
    }


def where_did_my_money_go(*, business, branch=None, date_from=None, date_to=None):
    """Explains cash flow using actual recorded transactions (spec
    section 22): money received vs. where it went (stock purchases,
    expenses, supplier payments, outstanding customer credit)."""
    from apps.expenses.models import Expense
    from apps.suppliers.models import SupplierLedgerEntry
    from apps.customers.models import CustomerCreditTransaction

    def scope(qs, field="created_at"):
        if branch and hasattr(qs.model, "branch"):
            qs = qs.filter(branch=branch)
        if date_from:
            qs = qs.filter(**{f"{field}__gte": date_from})
        if date_to:
            qs = qs.filter(**{f"{field}__lte": date_to})
        return qs

    money_received = scope(Sale.objects.filter(business=business, status__in=["completed", "partially_refunded"])).aggregate(
        total=Sum("grand_total")
    )["total"] or Decimal("0")

    stock_purchases = scope(SupplierLedgerEntry.objects.filter(business=business, entry_type="purchase")).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    expenses_total = scope(Expense.objects.filter(business=business, status="approved")).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    supplier_payments = scope(SupplierLedgerEntry.objects.filter(business=business, entry_type="payment")).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    supplier_payments = abs(supplier_payments)

    outstanding_credit_extended = scope(
        CustomerCreditTransaction.objects.filter(business=business, entry_type="credit_sale")
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    accounted_for = stock_purchases + expenses_total + supplier_payments + outstanding_credit_extended
    cash_remaining = money_received - accounted_for

    return {
        "money_received": money_received,
        "breakdown": {
            "stock_purchases": stock_purchases,
            "expenses": expenses_total,
            "supplier_payments": supplier_payments,
            "outstanding_customer_credit": outstanding_credit_extended,
        },
        "cash_remaining": cash_remaining,
    }


def customer_debt_aging(*, business, branch=None, as_of=None):
    """Ages each customer's outstanding credit sales into buckets
    (spec section 15: Current, 1-30, 31-60, 61-90, Over 90 days
    overdue) using FIFO matching — payments and adjustments are
    applied against the oldest unpaid credit sale first, the same way
    a real accounts-receivable ledger ages debt. A credit sale's age
    is measured from its due_date if one was set, otherwise from the
    date it was recorded.
    """
    from apps.customers.models import Customer

    as_of = (as_of or timezone.now()).date()
    customers_qs = Customer.objects.filter(business=business, is_active=True)

    def bucket_for(age_days):
        if age_days <= 0:
            return "current"
        if age_days <= 30:
            return "1_30"
        if age_days <= 60:
            return "31_60"
        if age_days <= 90:
            return "61_90"
        return "over_90"

    totals = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"),
              "61_90": Decimal("0"), "over_90": Decimal("0")}
    customers_out = []

    for customer in customers_qs:
        txns = list(customer.credit_transactions.order_by("created_at"))
        # FIFO queue of unpaid debt-increasing entries: [remaining_amount, age_date]
        queue = []
        for t in txns:
            if t.amount > 0:
                queue.append([t.amount, t.due_date or t.created_at.date()])
            elif t.amount < 0:
                remaining_payment = -t.amount
                i = 0
                while remaining_payment > 0 and i < len(queue):
                    take = min(queue[i][0], remaining_payment)
                    queue[i][0] -= take
                    remaining_payment -= take
                    i += 1
                queue = [q for q in queue if q[0] > 0]

        customer_buckets = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"),
                             "61_90": Decimal("0"), "over_90": Decimal("0")}
        for remaining, age_date in queue:
            age_days = (as_of - age_date).days
            b = bucket_for(age_days)
            customer_buckets[b] += remaining
            totals[b] += remaining

        outstanding = sum(customer_buckets.values())
        if outstanding > 0:
            customers_out.append({
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "phone_number": customer.phone_number,
                "outstanding_balance": outstanding,
                "buckets": customer_buckets,
            })

    customers_out.sort(key=lambda c: c["outstanding_balance"], reverse=True)
    return {
        "as_of": as_of.isoformat(),
        "totals": totals,
        "total_outstanding": sum(totals.values()),
        "customers": customers_out,
    }


def daily_priorities(*, business, branch=None, top_n=8):
    """'What Should I Do Today' (spec section 24) — turns real,
    already-recorded data into a short, ranked action list instead of
    just another dashboard of numbers. Each item is deterministic and
    traceable to the record that generated it, never an AI guess."""
    from datetime import timedelta
    from apps.inventory.models import StockLevel
    from apps.products.models import ProductBatch
    from apps.shifts.models import Shift

    now = timezone.now()
    items = []

    # 1. Restock: products at/under reorder level, ranked by how far under.
    stock_qs = StockLevel.objects.filter(business=business).select_related("product")
    if branch:
        stock_qs = stock_qs.filter(branch=branch)
    low = [
        l for l in stock_qs
        if l.product.reorder_level and l.quantity <= l.product.reorder_level
    ]
    low.sort(key=lambda l: l.quantity - l.product.reorder_level)
    for l in low[:5]:
        items.append({
            "priority": "restock",
            "severity": "important",
            "message": f"Restock {l.product.name} — {l.quantity} left, reorder level is {l.product.reorder_level}.",
            "reference_type": "product", "reference_id": str(l.product.id),
        })

    # 2. Overdue customers — anyone with an outstanding balance whose
    # oldest unpaid credit sale is now overdue (uses the same aging
    # logic as the debt-aging report, so the two never disagree).
    aging = customer_debt_aging(business=business, branch=branch, as_of=now)
    overdue_customers = [
        c for c in aging["customers"]
        if (c["buckets"]["1_30"] + c["buckets"]["31_60"] + c["buckets"]["61_90"] + c["buckets"]["over_90"]) > 0
    ]
    for c in overdue_customers[:3]:
        items.append({
            "priority": "collect_debt",
            "severity": "important",
            "message": f"Follow up with {c['customer_name']} — owes {c['outstanding_balance']} and is overdue.",
            "reference_type": "customer", "reference_id": c["customer_id"],
        })

    # 3. Unresolved cash discrepancies from recent shifts.
    shift_qs = Shift.objects.filter(business=business, status="pending_review")
    if branch:
        shift_qs = shift_qs.filter(branch=branch)
    for s in shift_qs.order_by("-closed_at")[:3]:
        if s.variance:
            items.append({
                "priority": "investigate_cash",
                "severity": "critical" if abs(s.variance) > 10000 else "important",
                "message": f"Review {s.employee.get_full_name() or s.employee.email}'s shift — cash variance of {s.variance}.",
                "reference_type": "shift", "reference_id": str(s.id),
            })

    # 4. Products expiring soon (within 14 days).
    soon = now.date() + timedelta(days=14)
    batch_qs = ProductBatch.objects.filter(
        product__business=business, expiry_date__isnull=False, expiry_date__lte=soon, expiry_date__gte=now.date(),
    ).select_related("product")
    if branch:
        batch_qs = batch_qs.filter(branch=branch)
    expiring = batch_qs.order_by("expiry_date")[:5]
    if expiring:
        names = ", ".join(sorted({b.product.name for b in expiring}))
        items.append({
            "priority": "expiring_stock",
            "severity": "important",
            "message": f"{len(expiring)} batch(es) expiring within 14 days: {names}.",
            "reference_type": "product_batch", "reference_id": None,
        })

    severity_rank = {"critical": 0, "important": 1, "info": 2}
    items.sort(key=lambda i: severity_rank.get(i["severity"], 3))
    return items[:top_n]


def business_health(*, business, branch=None):
    """Simple, explainable operational indicators (spec section 23) —
    not a single opaque score. good/attention/critical per area."""
    from apps.customers.models import CustomerCreditTransaction
    from apps.inventory.models import StockLevel

    def status_for(ratio_bad, ratio_ok=0.5):
        if ratio_bad >= ratio_ok:
            return "critical"
        if ratio_bad > 0:
            return "attention"
        return "good"

    stock_qs = StockLevel.objects.filter(business=business)
    if branch:
        stock_qs = stock_qs.filter(branch=branch)
    levels = list(stock_qs.select_related("product"))
    low = [l for l in levels if l.product.reorder_level and l.quantity <= l.product.reorder_level]
    stock_control = status_for(len(low) / len(levels)) if levels else "good"

    debt_total = CustomerCreditTransaction.objects.filter(business=business).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    debt_control = "critical" if debt_total > Decimal("500000") else ("attention" if debt_total > 0 else "good")

    return {
        "stock_control": stock_control,
        "debt_management": debt_control,
        "low_stock_items": len(low),
        "total_customer_debt": debt_total,
    }


def inventory_profitability(*, business, branch=None, stale_days=30):
    """Per-product and shop-wide profit picture (gain/loss per item
    and in total), plus which products are 'old stock' — sitting with
    no sale in `stale_days` — worth a price review before they become
    a loss the owner didn't see coming.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.products.models import Product
    from apps.inventory.models import StockLevel, StockMovement

    stock_qs = StockLevel.objects.filter(business=business, quantity__gt=0)
    if branch:
        stock_qs = stock_qs.filter(branch=branch)
    levels = list(stock_qs.select_related("product"))

    cutoff = timezone.now() - timedelta(days=stale_days)
    last_sale_by_product = dict(
        StockMovement.objects.filter(business=business, reason="sale")
        .values("product").annotate(last_sale=Max("created_at"))
        .values_list("product", "last_sale")
    )

    products_out = []
    total_cost_value = Decimal("0")
    total_retail_value = Decimal("0")

    seen_products = set()
    for level in levels:
        p: Product = level.product
        if p.id in seen_products:
            continue
        seen_products.add(p.id)
        qty = level.quantity
        cost_value = qty * p.cost_price
        retail_value = qty * p.selling_price
        total_cost_value += cost_value
        total_retail_value += retail_value

        last_sale = last_sale_by_product.get(p.id)
        is_stale = last_sale is None or last_sale < cutoff

        products_out.append({
            "product_id": str(p.id),
            "product_name": p.name,
            "quantity_on_hand": qty,
            "cost_price": p.cost_price,
            "selling_price": p.selling_price,
            "profit_per_unit": p.profit_amount,
            "profit_margin_percent": p.profit_margin_percent,
            "is_at_loss": p.is_at_loss,
            "potential_profit": retail_value - cost_value,
            "is_old_stock": is_stale,
            "last_sale_at": last_sale.isoformat() if last_sale else None,
        })

    at_loss = [x for x in products_out if x["is_at_loss"]]
    old_stock_needing_review = [x for x in products_out if x["is_old_stock"] and not x["is_at_loss"]]

    return {
        "total_cost_value": total_cost_value,
        "total_retail_value": total_retail_value,
        "total_potential_profit": total_retail_value - total_cost_value,
        "products": sorted(products_out, key=lambda x: x["is_at_loss"], reverse=True),
        "products_at_loss": at_loss,
        "old_stock_needing_price_review": old_stock_needing_review,
    }


def sales_trend(*, business, branch=None, days=7):
    """Daily sales totals for the last N days — feeds the dashboard's
    collapsible bar chart. Days with zero sales are included as 0,
    not skipped, so the chart's x-axis stays evenly spaced."""
    from datetime import timedelta

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    sales_qs = Sale.objects.filter(
        business=business, status__in=["completed", "partially_refunded"],
        created_at__date__gte=start, created_at__date__lte=today,
    )
    if branch:
        sales_qs = sales_qs.filter(branch=branch)

    by_day = {}
    for row in sales_qs.values("created_at__date").annotate(total=Sum("grand_total")):
        by_day[row["created_at__date"]] = row["total"] or Decimal("0")

    return [
        {"date": (start + timedelta(days=i)).isoformat(), "total": by_day.get(start + timedelta(days=i), Decimal("0"))}
        for i in range(days)
    ]
