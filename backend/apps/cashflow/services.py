import calendar
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

MIN_DAYS_SALES_HISTORY = 14  # below this, an "average daily cash-in" figure is noise


def _due_date_in_month(year: int, month: int, day_of_month: int):
    last_day = calendar.monthrange(year, month)[1]
    return day_of_month if day_of_month <= last_day else last_day


def cash_flow_forecast(*, business, days_ahead=30, branch=None):
    """Cash-Flow Danger-Day Forecast (differentiator feature) — plain
    arithmetic, not AI: compares the business's own average daily
    sales revenue (last 30 days) against its owner-declared recurring
    obligations (RecurringExpenseSchedule) landing in the next
    `days_ahead` days. A "danger day" is a day where a single
    scheduled obligation (or the sum of several landing the same day)
    exceeds what the business typically brings in on an average day —
    worth knowing about before it happens, not after.

    This is deliberately NOT a running bank-balance simulation: the
    app doesn't track an actual live cash balance, so pretending to
    project one forward would be presenting a guess as a fact. Each
    day is evaluated independently against the average, which is
    exactly what the underlying data can honestly support.
    """
    from apps.sales.models import Sale
    from .models import RecurringExpenseSchedule

    now = timezone.now()
    history_start = (now - timedelta(days=30)).date()
    sales_qs = Sale.objects.filter(business=business, status="completed", created_at__date__gte=history_start)
    if branch:
        sales_qs = sales_qs.filter(branch=branch)

    days_with_sales = sales_qs.values_list("created_at__date", flat=True).distinct().count()
    total_revenue = sum((s.grand_total for s in sales_qs), Decimal("0"))

    if days_with_sales < MIN_DAYS_SALES_HISTORY:
        return {
            "insufficient_data": True,
            "reason": f"Fewer than {MIN_DAYS_SALES_HISTORY} days of sales history in the last 30 days — "
                      f"not enough to establish a reliable average daily cash-in yet.",
            "average_daily_cash_in": None,
            "danger_days": [],
        }

    average_daily_cash_in = total_revenue / 30  # over the calendar window, not just days with sales — a
    # zero-sales day is real information about the business's cash rhythm, not a gap to skip over.

    schedules = RecurringExpenseSchedule.objects.filter(business=business, is_active=True)
    if branch:
        from django.db.models import Q
        schedules = schedules.filter(Q(branch=branch) | Q(branch__isnull=True))

    danger_days = []
    for offset in range(days_ahead):
        day = (now + timedelta(days=offset)).date()
        due_today = [s for s in schedules if _due_date_in_month(day.year, day.month, s.day_of_month) == day.day]
        if not due_today:
            continue
        total_due = sum((s.amount for s in due_today), Decimal("0"))
        if total_due > average_daily_cash_in:
            danger_days.append({
                "date": day.isoformat(),
                "days_from_now": offset,
                "expected_outflow": str(total_due),
                "average_daily_cash_in": str(average_daily_cash_in),
                "shortfall": str(total_due - average_daily_cash_in),
                "items": [{"name": s.name, "amount": str(s.amount)} for s in due_today],
            })

    return {
        "insufficient_data": False,
        "average_daily_cash_in": str(average_daily_cash_in),
        "days_with_sales_in_last_30": days_with_sales,
        "danger_days": danger_days,
    }
