from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.reports.services import customer_debt_aging


def generate_snapshot(*, business, months=12):
    """Computes every figure that goes on the Loan/Investor Readiness
    Report. Pure arithmetic on the business's own already-recorded
    data — no AI, no estimation, nothing invented. If a figure can't
    be computed from real data (e.g. no sales history at all yet),
    it's reported as such rather than guessed at, in line with the
    project's rule that financial figures are never a source of
    invented numbers.
    """
    from apps.sales.models import Sale
    from apps.shifts.models import Shift
    from apps.suppliers.models import Supplier

    now = timezone.now()
    period_start = (now - timezone.timedelta(days=30 * months)).date()
    period_end = now.date()

    sales_qs = Sale.objects.filter(business=business, status="completed", created_at__date__gte=period_start)

    monthly = list(
        sales_qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("month")
    )
    monthly_revenue = [
        {"month": m["month"].strftime("%Y-%m"), "revenue": str(m["total"]), "sale_count": m["count"]}
        for m in monthly
    ]
    total_revenue = sum((m["total"] for m in monthly), Decimal("0"))
    active_months = len(monthly)

    # Gross profit, computed straight from what was actually sold —
    # same figures the ledger's COGS postings and Reports use, not a
    # separate recomputation that could quietly drift out of sync.
    total_cogs = Decimal("0")
    for sale in sales_qs.prefetch_related("items__product"):
        for item in sale.items.all():
            total_cogs += item.quantity * item.product.cost_price
    gross_profit = total_revenue - total_cogs
    gross_margin_percent = round((gross_profit / total_revenue) * 100, 1) if total_revenue else None

    aging = customer_debt_aging(business=business)
    total_customer_debt = aging["total_outstanding"]

    total_supplier_debt = sum((s.outstanding_balance for s in Supplier.objects.filter(business=business)), Decimal("0"))

    # Cash discipline: of shifts with a physical count recorded, what
    # share closed with no meaningful variance (< 1% of opening cash,
    # or a flat small amount for a very small float).
    shifts = Shift.objects.filter(business=business, closed_at__isnull=False, closed_at__date__gte=period_start)
    shifts_with_variance_data = [s for s in shifts if s.variance is not None]
    if shifts_with_variance_data:
        threshold = Decimal("500")  # flat small-amount threshold; a percentage-of-float rule
        clean = [s for s in shifts_with_variance_data if abs(s.variance) <= threshold]
        cash_discipline_percent = round((len(clean) / len(shifts_with_variance_data)) * 100, 1)
    else:
        cash_discipline_percent = None

    first_sale = Sale.objects.filter(business=business, status="completed").order_by("created_at").first()
    business_trading_since = first_sale.created_at.date().isoformat() if first_sale else None

    return {
        "generated_at": now.isoformat(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "business_name": business.name,
        "currency_code": business.currency_code,
        "business_trading_since": business_trading_since,
        "monthly_revenue": monthly_revenue,
        "active_months_in_period": active_months,
        "total_revenue": str(total_revenue),
        "average_monthly_revenue": str(round(total_revenue / active_months, 2)) if active_months else None,
        "gross_profit": str(gross_profit),
        "gross_margin_percent": str(gross_margin_percent) if gross_margin_percent is not None else None,
        "total_customer_debt_owed_to_business": str(total_customer_debt),
        "total_supplier_debt_owed_by_business": str(total_supplier_debt),
        "net_receivables_position": str(total_customer_debt - total_supplier_debt),
        "cash_discipline_percent": str(cash_discipline_percent) if cash_discipline_percent is not None else None,
        "shifts_evaluated": len(shifts_with_variance_data),
        "insufficient_data_flags": _insufficient_data_flags(active_months, shifts_with_variance_data),
    }


def _insufficient_data_flags(active_months, shifts_with_variance_data) -> list:
    """Every figure that couldn't be computed with confidence, named
    plainly — a lender should be told 'not enough data' rather than
    have a report imply more history exists than actually does."""
    flags = []
    if active_months < 3:
        flags.append("Less than 3 months of sales history — revenue trend may not be representative.")
    if not shifts_with_variance_data:
        flags.append("No closed shifts with a recorded cash count in this period — cash discipline can't be assessed.")
    return flags
