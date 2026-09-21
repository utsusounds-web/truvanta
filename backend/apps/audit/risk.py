"""Rule-based, explainable risk detection (spec section 13). Every
alert is a plain description of the pattern plus the underlying
records it's based on — never an accusation, never a black-box score.
Future ML ranking can sit on top of this without changing the
contract: an alert always names the rule and the evidence.
"""
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.utils import timezone

from apps.sales.models import Sale
from apps.returns.models import SaleReturn
from .models import AuditLog


@dataclass
class RiskAlert:
    rule: str
    message: str
    severity: str  # "info" | "attention" | "critical"
    evidence_ids: list = field(default_factory=list)


def _excessive_discounts(business, branch, since, threshold_ratio=Decimal("0.20")):
    alerts = []
    sales = Sale.objects.filter(business=business, branch=branch, created_at__gte=since, status="completed")
    for sale in sales:
        if sale.subtotal and (sale.discount_total / sale.subtotal) > threshold_ratio:
            alerts.append(RiskAlert(
                rule="excessive_discount",
                message=f"Sale {sale.transaction_number} had a discount above {int(threshold_ratio*100)}% of subtotal.",
                severity="attention",
                evidence_ids=[str(sale.id)],
            ))
    return alerts


def _frequent_reprints(business, branch, since, threshold=3):
    alerts = []
    counts = (
        AuditLog.objects.filter(business=business, branch=branch, action="receipt_reprint", created_at__gte=since)
        .values("actor").annotate(n=Count("id")).filter(n__gte=threshold)
    )
    for row in counts:
        alerts.append(RiskAlert(
            rule="frequent_reprints",
            message=f"A staff member reprinted receipts {row['n']} times in the period — worth a quick check.",
            severity="attention",
            evidence_ids=[str(row["actor"])] if row["actor"] else [],
        ))
    return alerts


def _repeated_cancellations(business, branch, since, threshold=3):
    alerts = []
    counts = (
        AuditLog.objects.filter(business=business, branch=branch, action="cancellation", created_at__gte=since)
        .values("actor").annotate(n=Count("id")).filter(n__gte=threshold)
    )
    for row in counts:
        alerts.append(RiskAlert(
            rule="repeated_cancellations",
            message=f"A staff member cancelled {row['n']} sales in the period — unusual pattern, worth review.",
            severity="attention",
            evidence_ids=[str(row["actor"])] if row["actor"] else [],
        ))
    return alerts


def _unusual_hours_sales(business, branch, since, open_hour=6, close_hour=22):
    alerts = []
    sales = Sale.objects.filter(business=business, branch=branch, created_at__gte=since, status="completed")
    outside = [s for s in sales if s.created_at.hour < open_hour or s.created_at.hour >= close_hour]
    if outside:
        alerts.append(RiskAlert(
            rule="outside_business_hours",
            message=f"{len(outside)} sale(s) were recorded outside normal business hours.",
            severity="attention",
            evidence_ids=[str(s.id) for s in outside[:10]],
        ))
    return alerts


def _large_refunds(business, branch, since, threshold=Decimal("20000")):
    alerts = []
    big = SaleReturn.objects.filter(
        business=business, sale__branch=branch, return_type="refund",
        refund_amount__gte=threshold, created_at__gte=since,
    )
    for r in big:
        alerts.append(RiskAlert(
            rule="large_refund",
            message=f"A refund of {r.refund_amount} was recorded on {r.sale.transaction_number}.",
            severity="attention",
            evidence_ids=[str(r.id)],
        ))
    return alerts


def scan_branch(*, business, branch, days=7):
    """Run all rules over the last `days` days for one branch."""
    since = timezone.now() - timedelta(days=days)
    alerts = []
    alerts += _excessive_discounts(business, branch, since)
    alerts += _frequent_reprints(business, branch, since)
    alerts += _repeated_cancellations(business, branch, since)
    alerts += _unusual_hours_sales(business, branch, since)
    alerts += _large_refunds(business, branch, since)
    return alerts
