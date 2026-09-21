"""Platform Usage Analytics — 'how many people use the app', built
from real data, no vanity metrics. This is the platform owner's own
view across every business on the deployment, distinct from anything
a business owner sees about their own business.
"""
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone


def platform_usage_summary():
    from apps.accounts.models import User, Membership
    from apps.tenants.models import Business, Branch
    from apps.sales.models import Sale
    from .models import Subscription

    now = timezone.now()
    last_30 = now - timedelta(days=30)
    last_7 = now - timedelta(days=7)

    total_businesses = Business.objects.count()
    total_branches = Branch.objects.count()
    total_users = User.objects.filter(is_active=True).count()
    total_staff_memberships = Membership.objects.filter(is_active=True).count()

    active_users_30d = User.objects.filter(last_login__gte=last_30).count()
    active_users_7d = User.objects.filter(last_login__gte=last_7).count()

    businesses_with_a_sale_30d = (
        Sale.objects.filter(status="completed", created_at__gte=last_30)
        .values("business_id").distinct().count()
    )

    subs_by_status = dict(
        Subscription.objects.values_list("status").annotate(count=Count("id")).values_list("status", "count")
    )
    subs_by_plan = list(
        Subscription.objects.filter(status="active").values("plan__name", "plan__billing_interval")
        .annotate(count=Count("id")).order_by("-count")
    )

    signups_last_30d = (
        Business.objects.filter(created_at__gte=last_30)
        .annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id")).order_by("day")
    )

    return {
        "generated_at": now.isoformat(),
        "totals": {
            "businesses": total_businesses,
            "branches": total_branches,
            "users": total_users,
            "staff_memberships": total_staff_memberships,
        },
        "activity": {
            "active_users_last_7_days": active_users_7d,
            "active_users_last_30_days": active_users_30d,
            "businesses_that_made_a_sale_last_30_days": businesses_with_a_sale_30d,
            "businesses_with_no_sale_last_30_days": total_businesses - businesses_with_a_sale_30d,
        },
        "subscriptions": {
            "by_status": subs_by_status,
            "by_plan": [
                {"plan_name": p["plan__name"], "billing_interval": p["plan__billing_interval"], "count": p["count"]}
                for p in subs_by_plan
            ],
        },
        "signups_last_30_days": [
            {"date": s["day"].isoformat(), "count": s["count"]} for s in signups_last_30d
        ],
    }
