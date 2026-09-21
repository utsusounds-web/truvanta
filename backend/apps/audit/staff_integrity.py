"""Staff Integrity Score (differentiator feature) — turns data the
business is already recording (discounts, refunds, cancellations,
stock adjustments, cash variances, all already in AuditLog and Shift)
into a private, owner-only signal: is this person's rate of
exceptions normal for this business, or worth a conversation?

Deliberately NOT a punitive 0-100 "score" — that invites treating a
single number as gospel and would be exactly the kind of thing this
project's own rules warn against (never let a derived figure replace
real judgment). Instead: a plain rate, shown next to the business's
own average, with a category — "typical", "above average", or "not
enough data yet" — a person reads and interprets themselves.
"""
from decimal import Decimal

from apps.accounts.models import Membership

EXCEPTION_ACTIONS = ["discount", "return", "cancellation", "stock_adjustment", "credit_change"]
MIN_SALES_FOR_RATING = 15  # below this, a rate is noise, not signal


def staff_integrity_summary(*, business, branch=None):
    from apps.audit.models import AuditLog
    from apps.sales.models import Sale
    from apps.shifts.models import Shift

    memberships = Membership.objects.filter(business=business).select_related("user", "role")
    if branch:
        memberships = memberships.filter(branch=branch) | memberships.filter(branch__isnull=True)
    staff_users = {m.user for m in memberships}

    sales_qs = Sale.objects.filter(business=business, status="completed")
    if branch:
        sales_qs = sales_qs.filter(branch=branch)

    audit_qs = AuditLog.objects.filter(business=business, action__in=EXCEPTION_ACTIONS)
    if branch:
        audit_qs = audit_qs.filter(branch=branch)

    shifts_qs = Shift.objects.filter(business=business, variance__isnull=False)
    if branch:
        shifts_qs = shifts_qs.filter(branch=branch)

    rows = []
    business_total_sales = 0
    business_total_exceptions = 0

    per_user_data = {}
    for user in staff_users:
        sales_count = sales_qs.filter(cashier=user).count()
        exceptions_count = audit_qs.filter(actor=user).count()
        user_shifts = list(shifts_qs.filter(employee=user))
        avg_variance = (
            sum((abs(s.variance) for s in user_shifts), Decimal("0")) / len(user_shifts)
            if user_shifts else None
        )
        per_user_data[user.id] = {
            "user": user, "sales_count": sales_count, "exceptions_count": exceptions_count,
            "avg_absolute_variance": avg_variance, "shifts_count": len(user_shifts),
        }
        business_total_sales += sales_count
        business_total_exceptions += exceptions_count

    business_avg_rate = (
        (business_total_exceptions / business_total_sales) * 100 if business_total_sales else None
    )

    for user_id, data in per_user_data.items():
        sales_count = data["sales_count"]
        if sales_count < MIN_SALES_FOR_RATING:
            category = "insufficient_data"
            rate_per_100 = None
        else:
            rate_per_100 = round((data["exceptions_count"] / sales_count) * 100, 1)
            if business_avg_rate is None:
                category = "insufficient_data"
            elif rate_per_100 > business_avg_rate * 1.5 and rate_per_100 - business_avg_rate > 2:
                category = "above_average"
            else:
                category = "typical"

        rows.append({
            "user_id": str(data["user"].id),
            "user_name": data["user"].get_full_name() or data["user"].email,
            "sales_count": sales_count,
            "exceptions_count": data["exceptions_count"],
            "exception_rate_per_100_sales": rate_per_100,
            "avg_absolute_cash_variance": str(data["avg_absolute_variance"]) if data["avg_absolute_variance"] is not None else None,
            "shifts_count": data["shifts_count"],
            "category": category,
        })

    rows.sort(key=lambda r: (r["exception_rate_per_100_sales"] is None, -(r["exception_rate_per_100_sales"] or 0)))

    return {
        "business_average_exception_rate_per_100_sales": round(business_avg_rate, 1) if business_avg_rate is not None else None,
        "minimum_sales_for_rating": MIN_SALES_FOR_RATING,
        "staff": rows,
    }
