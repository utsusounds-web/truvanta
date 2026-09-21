from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.risk import scan_branch
from apps.billing.services import business_has_feature
from apps.core.permissions import IsBusinessMember, HasBusinessPermission
from apps.tenants.models import Business, Branch
from . import services
from .exports import (
    profitability_csv, owner_dashboard_csv, expenses_csv, customer_statement_csv, ledger_statement_csv,
)


class RequireViewProfit(HasBusinessPermission):
    required_permission_code = "view_profit"


def _require_csv_export_allowed(request):
    """CSV export specifically is the paid part of reporting — the
    dashboards themselves stay free. Checked inline rather than as a
    view-level permission so the same endpoint can keep serving the
    core (free) dashboard when export isn't allowed."""
    if not business_has_feature(request.business_id, "advanced_reports"):
        raise PermissionDenied("CSV export isn't included in your current plan.")


class OwnerDashboardView(APIView):
    permission_classes = [IsBusinessMember]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        data = services.owner_dashboard(
            business=business, branch=branch,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        if request.query_params.get("export") == "csv":
            _require_csv_export_allowed(request)
            return owner_dashboard_csv(data)
        return Response(data)


class SalesTrendView(APIView):
    """Daily sales totals for the last N days — feeds the dashboard's
    collapsible bar chart. Same free/paid boundary as the rest of the
    dashboard: this is core, not an export."""
    permission_classes = [IsBusinessMember]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        days = int(request.query_params.get("days", 7))
        data = services.sales_trend(business=business, branch=branch, days=max(1, min(days, 30)))
        return Response(data)


class WhereDidMyMoneyGoView(APIView):
    # "Where did my money go" is a full cash-flow/profit breakdown —
    # exactly the "confidential profit information" the spec says
    # sales staff shouldn't see, so it needs the explicit permission
    # rather than just plain business membership.
    permission_classes = [RequireViewProfit]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        data = services.where_did_my_money_go(
            business=business, branch=branch,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(data)


class BusinessHealthView(APIView):
    permission_classes = [IsBusinessMember]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        return Response(services.business_health(business=business, branch=branch))


class RiskAlertsView(APIView):
    permission_classes = [IsBusinessMember]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch_id = request.query_params.get("branch")
        branches = Branch.objects.filter(business=business, pk=branch_id) if branch_id else Branch.objects.filter(business=business)
        days = int(request.query_params.get("days", 7))
        results = []
        for branch in branches:
            for alert in scan_branch(business=business, branch=branch, days=days):
                results.append({
                    "branch": branch.name, "rule": alert.rule, "message": alert.message,
                    "severity": alert.severity, "evidence_ids": alert.evidence_ids,
                })
        return Response(results)


def debt_aging_csv(data: dict):
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="debt-aging.csv"'
    writer = csv.writer(response)
    writer.writerow([f"Debt aging as of {data['as_of']}"])
    writer.writerow([])
    writer.writerow(["Customer", "Phone", "Outstanding", "Current", "1-30 days", "31-60 days", "61-90 days", "Over 90 days"])
    for c in data["customers"]:
        b = c["buckets"]
        writer.writerow([
            c["customer_name"], c["phone_number"], c["outstanding_balance"],
            b["current"], b["1_30"], b["31_60"], b["61_90"], b["over_90"],
        ])
    writer.writerow([])
    t = data["totals"]
    writer.writerow(["TOTAL", "", data["total_outstanding"], t["current"], t["1_30"], t["31_60"], t["61_90"], t["over_90"]])
    return response


class DebtAgingView(APIView):
    # Same reasoning as WhereDidMyMoneyGoView: this is customer-debt
    # exposure across the whole business, which is financial data the
    # spec treats the same as profit — gated accordingly.
    permission_classes = [RequireViewProfit]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        data = services.customer_debt_aging(business=business, branch=branch)
        if request.query_params.get("export") == "csv":
            _require_csv_export_allowed(request)
            return debt_aging_csv(data)
        return Response(data)


class DailyPrioritiesView(APIView):
    # Not gated on view_profit — a cashier benefits from "restock this"
    # and "this batch is expiring" just as much as an owner does. The
    # underlying debt-aging figures used to build the list stay
    # business-only in this response (customer names/amounts aren't
    # included, only the summary sentence), so nothing profit-sensitive
    # leaks through to someone without that permission.
    permission_classes = [IsBusinessMember]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        items = services.daily_priorities(business=business, branch=branch)
        if not request.membership.has_permission("view_profit"):
            items = [i for i in items if i["priority"] != "collect_debt"]
        return Response({"items": items})


class InventoryProfitabilityView(APIView):
    permission_classes = [RequireViewProfit]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        stale_days = int(request.query_params.get("stale_days", 30))
        data = services.inventory_profitability(business=business, branch=branch, stale_days=stale_days)
        if request.query_params.get("export") == "csv":
            _require_csv_export_allowed(request)
            return profitability_csv(data)
        return Response(data)


class StatementExportView(APIView):
    """One page, one place, to download any of the business's
    statements as CSV — sales, expenses, a specific customer's
    account, the ledger, or inventory profitability — each scoped to
    a date range where that's meaningful. Every statement type is a
    real accounting/business record, not a raw table dump, so this
    reuses the same permission and billing gates the rest of Reports
    already enforces rather than introducing a new set of rules.
    """
    permission_classes = [IsBusinessMember]

    def get(self, request):
        _require_csv_export_allowed(request)
        statement_type = request.query_params.get("type")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        business = Business.objects.get(pk=request.business_id)
        accessible = request.accessible_branch_ids

        def scoped(qs, branch_field="branch_id"):
            if accessible is not None:
                qs = qs.filter(**{f"{branch_field}__in": accessible})
            return qs

        if statement_type == "sales":
            if not request.membership.has_permission("view_profit"):
                raise PermissionDenied("You don't have access to sales statements.")
            from apps.sales.models import Sale
            qs = Sale.objects.filter(business=business, status="completed").select_related(
                "branch", "cashier", "customer")
            if date_from: qs = qs.filter(created_at__gte=date_from)
            if date_to: qs = qs.filter(created_at__lte=date_to)
            from apps.reports.exports import sales_csv
            return sales_csv(scoped(qs))

        if statement_type == "expenses":
            if not request.membership.has_permission("view_profit"):
                raise PermissionDenied("You don't have access to expense statements.")
            from apps.expenses.models import Expense
            qs = Expense.objects.filter(business=business).exclude(status="voided").select_related(
                "branch", "category", "requested_by", "approved_by")
            if date_from: qs = qs.filter(created_at__gte=date_from)
            if date_to: qs = qs.filter(created_at__lte=date_to)
            return expenses_csv(scoped(qs))

        if statement_type == "customer":
            # Not gated on view_profit — a customer's own account
            # balance isn't the business's profit data, and any staff
            # member following up on a debt needs to be able to pull
            # it, same as the Customers page they already see it on.
            customer_id = request.query_params.get("customer")
            if not customer_id:
                raise ValidationError("A customer must be specified.")
            from apps.customers.models import Customer
            customer = Customer.objects.get(pk=customer_id, business=business)
            qs = customer.credit_transactions.select_related("recorded_by")
            if date_from: qs = qs.filter(created_at__gte=date_from)
            if date_to: qs = qs.filter(created_at__lte=date_to)
            return customer_statement_csv(customer, qs)

        if statement_type == "ledger":
            if not request.membership.has_permission("view_profit"):
                raise PermissionDenied("You don't have access to the ledger statement.")
            from apps.ledger.models import JournalEntry
            qs = JournalEntry.objects.filter(business=business).select_related("branch").prefetch_related(
                "lines__account")
            if date_from: qs = qs.filter(entry_date__gte=date_from)
            if date_to: qs = qs.filter(entry_date__lte=date_to)
            return ledger_statement_csv(scoped(qs, branch_field="branch_id"))

        if statement_type == "profitability":
            if not request.membership.has_permission("view_profit"):
                raise PermissionDenied("You don't have access to profitability statements.")
            branch = None
            if request.query_params.get("branch"):
                branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
            data = services.inventory_profitability(business=business, branch=branch)
            return profitability_csv(data)

        if statement_type == "debt_aging":
            if not request.membership.has_permission("view_profit"):
                raise PermissionDenied("You don't have access to debt aging statements.")
            data = services.customer_debt_aging(business=business)
            return debt_aging_csv(data)

        raise ValidationError(
            "Unknown statement type. Choose one of: sales, expenses, customer, ledger, profitability, debt_aging."
        )
