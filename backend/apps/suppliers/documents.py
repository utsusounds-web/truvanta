"""A4 documents for the supplier/purchasing side (spec section 16):
Purchase Order (to send a supplier), Goods-Received Report (proof of
what was actually received, discrepancies included), and Supplier
Statement (running account with a supplier, for reconciling what's
owed).
"""
from apps.core.pdf import DocumentPDF


def generate_purchase_order_pdf(purchase_order) -> bytes:
    branding = purchase_order.branch.branding_context
    doc = DocumentPDF(branding, "Purchase Order", purchase_order.reference_number)

    doc.two_col("Supplier:", purchase_order.supplier.name, bold=True)
    if purchase_order.supplier.phone_number:
        doc.text(purchase_order.supplier.phone_number, size=8.5)
    if purchase_order.supplier.address:
        doc.text(purchase_order.supplier.address, size=8.5)
    doc.two_col("Status:", purchase_order.get_status_display())
    doc.two_col("Branch:", purchase_order.branch.name)
    doc.spacer(4)

    items = list(purchase_order.items.select_related("product", "unit"))
    rows = [
        [item.product.name, item.unit.abbreviation, f"{item.quantity_ordered:g}",
         f"{item.unit_cost:,.2f}", f"{item.quantity_ordered * item.unit_cost:,.2f}"]
        for item in items
    ]
    doc.table(
        headers=["Product", "Unit", "Qty", "Unit Cost", "Line Total"],
        rows=rows, col_widths=[70, 20, 20, 30, 34], align_right_from=2,
    )
    total = sum(item.quantity_ordered * item.unit_cost for item in items)
    doc.hr()
    doc.two_col("TOTAL", f"{branding['currency_code']} {total:,.2f}", bold=True, size=11)

    if purchase_order.notes:
        doc.spacer(6)
        doc.text(f"Notes: {purchase_order.notes}", size=8.5)

    return doc.finish()


def generate_goods_receipt_pdf(receipt) -> bytes:
    po = receipt.purchase_order
    branding = po.branch.branding_context
    doc = DocumentPDF(branding, "Goods Received", f"Against {po.reference_number}")

    doc.two_col("Supplier:", po.supplier.name, bold=True)
    doc.two_col("Received by:", receipt.received_by.get_full_name() or receipt.received_by.email if receipt.received_by else "—")
    doc.two_col("Date:", receipt.created_at.strftime("%Y-%m-%d %H:%M"))
    doc.spacer(4)

    items = list(receipt.items.select_related("purchase_order_item__product"))
    rows = []
    any_discrepancy = False
    for item in items:
        product = item.purchase_order_item.product
        ordered = item.purchase_order_item.quantity_ordered
        discrepancy = item.quantity_damaged or item.quantity_missing
        if discrepancy:
            any_discrepancy = True
        rows.append([
            product.name, f"{ordered:g}", f"{item.quantity_received:g}",
            f"{item.quantity_damaged:g}", f"{item.quantity_missing:g}",
        ])
    doc.table(
        headers=["Product", "Ordered", "Received", "Damaged", "Missing"],
        rows=rows, col_widths=[70, 25, 25, 25, 25], align_right_from=1,
    )

    if any_discrepancy:
        doc.spacer(6)
        doc.text("⚠ This receipt has discrepancies — see damaged/missing columns above.", size=9, bold=True)

    if receipt.notes:
        doc.spacer(4)
        doc.text(f"Notes: {receipt.notes}", size=8.5)

    return doc.finish()


def generate_supplier_statement_pdf(supplier, entries) -> bytes:
    branding = supplier.business.branding_context
    doc = DocumentPDF(branding, "Supplier Statement", supplier.name)

    doc.two_col("Outstanding balance:", f"{branding['currency_code']} {supplier.outstanding_balance:,.2f}", bold=True)
    doc.spacer(4)

    running = 0
    rows = []
    for e in entries:
        running += e.amount
        rows.append([
            e.created_at.strftime("%Y-%m-%d %H:%M"), e.get_entry_type_display(), e.reference_note or "—",
            f"{e.amount:,.2f}", f"{running:,.2f}",
        ])
    doc.table(
        headers=["Date", "Type", "Reference", "Amount", "Running Balance"],
        rows=rows, col_widths=[25, 30, 55, 32, 32], align_right_from=3,
    )

    return doc.finish()
