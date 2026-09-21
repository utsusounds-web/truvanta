"""Notification triggers that aren't tied to a single request-response
event (a sale, a shift close) — these are checked periodically instead.
There's no task queue (Celery) in this project yet, so these are
exposed two ways: as an API action the owner/frontend can trigger on
demand, and as a management command (`check_notifications`) a real
deployment can point a cron job at for the "automatic" version.
"""
from datetime import date

from django.db.models import Sum
from django.utils import timezone

from .services import notify


def check_overdue_debts(business, branch=None):
    """One alert summarizing every customer whose outstanding balance
    includes a credit sale past its due date — not one alert per
    customer, so this stays useful instead of becoming spam."""
    from apps.customers.models import Customer, CustomerCreditTransaction

    today = date.today()
    overdue_customer_ids = (
        CustomerCreditTransaction.objects.filter(
            business=business, entry_type="credit_sale", due_date__isnull=False, due_date__lt=today,
        ).values_list("customer_id", flat=True).distinct()
    )
    if not overdue_customer_ids:
        return None

    overdue_customers = []
    for customer in Customer.objects.filter(id__in=overdue_customer_ids):
        balance = customer.outstanding_balance
        if balance > 0:
            overdue_customers.append((customer.name, balance))

    if not overdue_customers:
        return None

    lines = "\n".join(f"- {name}: {balance}" for name, balance in overdue_customers[:10])
    more = f"\n...and {len(overdue_customers) - 10} more" if len(overdue_customers) > 10 else ""
    return notify(
        business=business, branch=branch, level="important",
        title=f"{len(overdue_customers)} customer(s) overdue on credit",
        message=f"These customers have credit sales past their due date:\n{lines}{more}",
        link_path="/customers",
    )


def send_daily_summary(business, branch):
    """A same-day sales summary — the 'daily sales summary' info
    notification called out in the spec's notification catalog."""
    from apps.sales.models import Sale

    today = timezone.now().date()
    sales_today = Sale.objects.filter(
        business=business, branch=branch, status__in=["completed", "partially_refunded"],
        created_at__date=today,
    )
    total = sales_today.aggregate(total=Sum("grand_total"))["total"] or 0
    count = sales_today.count()

    return notify(
        business=business, branch=branch, level="info",
        title=f"Today's sales at {branch.name}",
        message=f"{count} sale(s) totaling {total} so far today.",
        link_path="/dashboard",
    )


def check_low_stock(business, branch=None):
    """One alert summarizing every product at or below its reorder
    level — not one alert per product, for the same anti-spam reason
    as check_overdue_debts. This existed as a passive number on the
    dashboard and in the daily priorities list, but nothing ever
    pushed it to the owner the way an overdue debt or a subscription
    lapse does — meant to run daily (see check_notifications
    --low-stock), not hourly, since restocking doesn't change hour to
    hour the way debts can."""
    from apps.inventory.models import StockLevel

    stock_qs = StockLevel.objects.filter(business=business).select_related("product")
    if branch:
        stock_qs = stock_qs.filter(branch=branch)
    low = [
        level for level in stock_qs
        if level.product.reorder_level and level.quantity <= level.product.reorder_level
    ]
    if not low:
        return None

    low.sort(key=lambda level: level.quantity - level.product.reorder_level)
    lines = "\n".join(f"- {level.product.name}: {level.quantity} left (reorder level {level.product.reorder_level})" for level in low[:10])
    more = f"\n...and {len(low) - 10} more" if len(low) > 10 else ""
    return notify(
        business=business, branch=branch, level="important",
        title=f"{len(low)} product(s) low on stock",
        message=f"These are at or below their reorder level:\n{lines}{more}",
        link_path="/inventory",
    )


def check_expiring_subscriptions(business):
    """Warns before a trial or paid subscription lapses, at a few
    fixed thresholds (7 days out, 3 days out, the final day, and the
    day after access actually stops) rather than either total silence
    or re-sending on every run. Meant to run once a day — see
    check_notifications --expiring-subscriptions — not hourly, since
    firing more often than daily would either spam at each threshold
    or (worse) skip a threshold entirely depending on run timing.

    Silence before this existed meant a business's access could just
    stop one day with zero warning — jarring for a paying customer and
    exactly the kind of thing a 'professional' subscription product
    doesn't do.
    """
    from apps.billing.models import Subscription

    try:
        sub = Subscription.objects.get(business=business)
    except Subscription.DoesNotExist:
        return None
    if not sub.current_period_end or sub.status not in ("trialing", "active"):
        return None

    days_remaining = (sub.current_period_end.date() - timezone.now().date()).days
    kind = "free trial" if sub.status == "trialing" else "subscription"
    end_date = sub.current_period_end.date()

    if days_remaining == 7:
        return notify(
            business=business, level="info", title=f"Your {kind} ends in 7 days",
            message=f"Your {kind} ends on {end_date}. Subscribe or upgrade from Billing to keep "
                     f"everything working without interruption.",
            link_path="/billing",
        )
    if days_remaining == 3:
        return notify(
            business=business, level="important", title=f"Your {kind} ends in 3 days",
            message=f"Your {kind} ends on {end_date} — some features will lock afterward until "
                     f"you subscribe or renew.",
            link_path="/billing",
        )
    if days_remaining == 0:
        return notify(
            business=business, level="critical", title=f"Your {kind} ends today",
            message=f"Your {kind} ends today. Renew from Billing now to avoid any interruption.",
            link_path="/billing",
        )
    if days_remaining == -1:
        return notify(
            business=business, level="critical", title=f"Your {kind} has ended",
            message=f"Your {kind} ended on {end_date} — some features are now locked until you "
                     f"subscribe or renew. Your data is safe and nothing has been deleted.",
            link_path="/billing",
        )
    return None
