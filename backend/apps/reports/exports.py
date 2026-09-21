"""CSV export for reports. Kept deliberately simple (Python's stdlib
csv module, streamed as a plain HttpResponse) rather than a heavier
export library — these are business records an owner opens in Excel,
not large enough to need chunked/streaming generation.
"""
import csv

from django.http import HttpResponse


def sales_csv(sales) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales.csv"'
    writer = csv.writer(response)
    writer.writerow(["Receipt #", "Date", "Branch", "Cashier", "Customer", "Type", "Status",
                      "Subtotal", "Discount", "Tax", "Total"])
    for s in sales:
        writer.writerow([
            s.transaction_number, s.created_at.strftime("%Y-%m-%d %H:%M"), s.branch.name,
            s.cashier.get_full_name() or s.cashier.email, s.customer.name if s.customer else "",
            s.sale_type, s.status, s.subtotal, s.discount_total, s.tax_total, s.grand_total,
        ])
    return response


def profitability_csv(report: dict) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="profitability.csv"'
    writer = csv.writer(response)
    writer.writerow(["Product", "Qty on hand", "Cost price", "Selling price", "Profit/unit",
                      "Margin %", "At a loss?", "Potential profit", "Old stock?", "Last sale"])
    for p in report["products"]:
        writer.writerow([
            p["product_name"], p["quantity_on_hand"], p["cost_price"], p["selling_price"],
            p["profit_per_unit"], p["profit_margin_percent"], "Yes" if p["is_at_loss"] else "No",
            p["potential_profit"], "Yes" if p["is_old_stock"] else "No", p["last_sale_at"] or "",
        ])
    return response


def owner_dashboard_csv(data: dict) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="owner-dashboard.csv"'
    writer = csv.writer(response)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total sales", data["total_sales"]])
    writer.writerow(["Total discount given", data["total_discount_given"]])
    writer.writerow(["Number of sales", data["number_of_sales"]])
    writer.writerow(["Low stock product count", data["low_stock_product_count"]])
    writer.writerow(["Total customer debt", data["total_customer_debt"]])
    return response


def expenses_csv(expenses) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="expenses-statement.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Branch", "Category", "Reason", "Amount", "Status", "Requested by", "Approved by"])
    for e in expenses:
        writer.writerow([
            e.created_at.strftime("%Y-%m-%d %H:%M"), e.branch.name, e.category.name, e.reason, e.amount,
            e.status, e.requested_by.get_full_name() or e.requested_by.email if e.requested_by else "",
            e.approved_by.get_full_name() or e.approved_by.email if e.approved_by else "",
        ])
    return response


def customer_statement_csv(customer, transactions) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{customer.name}-statement.csv"'
    writer = csv.writer(response)
    writer.writerow([f"Statement of account — {customer.name}"])
    writer.writerow([f"Outstanding balance: {customer.outstanding_balance}"])
    writer.writerow([])
    writer.writerow(["Date", "Type", "Amount", "Reference", "Recorded by"])
    for t in transactions:
        writer.writerow([
            t.created_at.strftime("%Y-%m-%d %H:%M"), t.get_entry_type_display(), t.amount,
            t.reference_note, t.recorded_by.get_full_name() or t.recorded_by.email if t.recorded_by else "",
        ])
    return response


def ledger_statement_csv(entries) -> HttpResponse:
    """A period statement of the double-entry ledger — every posted
    journal entry with its lines, in date order. Distinct from the
    trial-balance endpoint (which is a point-in-time balance snapshot,
    not a period record) — this is the actual transaction history an
    accountant or auditor would ask for."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ledger-statement.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Description", "Branch", "Account", "Debit", "Credit", "Source"])
    for entry in entries:
        for line in entry.lines.all():
            writer.writerow([
                entry.entry_date.strftime("%Y-%m-%d %H:%M"), entry.description,
                entry.branch.name if entry.branch else "", f"{line.account.code} — {line.account.name}",
                line.debit or "", line.credit or "", entry.source_type,
            ])
    return response
