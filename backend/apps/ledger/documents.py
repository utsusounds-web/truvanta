"""Opening Statement of Affairs — a timestamped, printable record of a
business's financial starting point (see models.OpeningBalanceStatement),
the kind of document an accountant or a lender would recognize on sight.
"""
from apps.core.pdf import DocumentPDF


def generate_opening_balance_pdf(statement) -> bytes:
    branding = statement.business.branding_context
    doc = DocumentPDF(branding, "Opening Statement of Affairs", str(statement.as_of_date))

    doc.two_col("Business:", statement.business.name, bold=True)
    doc.two_col("As of:", str(statement.as_of_date))
    if statement.recorded_by:
        name = f"{statement.recorded_by.first_name} {statement.recorded_by.last_name}".strip() or statement.recorded_by.email
        doc.two_col("Recorded by:", name)
    doc.spacer(6)

    currency = branding["currency_code"]
    asset_rows = [
        ("Cash on hand", statement.cash_on_hand),
        ("Bank balance", statement.bank_balance),
        ("Accounts receivable (owed to you)", statement.accounts_receivable),
        ("Inventory value", statement.inventory_value),
        ("Equipment & fixed assets", statement.fixed_assets),
    ]
    asset_rows = [(label, amount) for label, amount in asset_rows if amount]
    doc.table(
        headers=["Assets", "Amount"],
        rows=[[label, f"{amount:,.2f}"] for label, amount in asset_rows],
        col_widths=[130, 40], align_right_from=1,
    )
    doc.two_col("Total assets", f"{currency} {statement.total_assets:,.2f}", bold=True)
    doc.spacer(6)

    liability_rows = [
        ("Accounts payable (owed to suppliers)", statement.accounts_payable),
        ("Loans payable", statement.loans_payable),
    ]
    liability_rows = [(label, amount) for label, amount in liability_rows if amount]
    if liability_rows:
        doc.table(
            headers=["Liabilities", "Amount"],
            rows=[[label, f"{amount:,.2f}"] for label, amount in liability_rows],
            col_widths=[130, 40], align_right_from=1,
        )
    doc.two_col("Total liabilities", f"{currency} {statement.total_liabilities:,.2f}", bold=True)
    doc.hr()
    doc.two_col("NET WORTH", f"{currency} {statement.net_worth:,.2f}", bold=True, size=11)

    doc.spacer(8)
    doc.text(
        "This figure becomes the business's Owner's Equity opening balance in the ledger. "
        "Every calculation from this point forward (profit, business health, net worth over time) "
        "builds on this starting position.",
        size=8,
    )

    return doc.finish()
