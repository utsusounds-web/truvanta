from apps.core.pdf import DocumentPDF


def generate_quotation_pdf(quotation) -> bytes:
    branding = quotation.branch.branding_context
    title = quotation.get_document_type_display()
    doc = DocumentPDF(branding, title, quotation.reference_number)

    if quotation.customer:
        doc.two_col("For:", quotation.customer.name, bold=True)
        if quotation.customer.phone_number:
            doc.text(quotation.customer.phone_number, size=8.5)
    doc.two_col("Date:", quotation.created_at.strftime("%Y-%m-%d %H:%M"))
    if quotation.valid_until:
        doc.two_col("Valid until:", quotation.valid_until.strftime("%Y-%m-%d"))
    doc.spacer(4)

    items = list(quotation.items.select_related("product", "unit"))
    rows = [
        [item.product.name, item.unit.abbreviation, f"{item.quantity:g}",
         f"{item.unit_price:,.2f}", f"{item.line_total:,.2f}"]
        for item in items
    ]
    doc.table(
        headers=["Item", "Unit", "Qty", "Unit Price", "Line Total"],
        rows=rows, col_widths=[70, 20, 20, 30, 34], align_right_from=2,
    )
    doc.hr()
    doc.two_col("TOTAL", f"{branding['currency_code']} {quotation.subtotal:,.2f}", bold=True, size=12)

    if quotation.document_type == "proforma_invoice":
        doc.spacer(6)
        doc.text("This is a proforma invoice — not a demand for payment already due, but a request to remit", size=8)
        doc.text("payment against the amount above before the order proceeds.", size=8)

    if quotation.notes:
        doc.spacer(4)
        doc.text(f"Notes: {quotation.notes}", size=8.5)

    return doc.finish()
