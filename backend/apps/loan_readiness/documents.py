from apps.core.pdf import DocumentPDF


def generate_loan_readiness_pdf(report) -> bytes:
    from apps.tenants.models import Business
    business = Business.objects.get(pk=report.business_id)
    branding = business.branding_context
    snap = report.snapshot_json

    doc = DocumentPDF(branding, "Business Financial Summary", f"Report #{str(report.id)[:8]}")

    doc.two_col("Period:", f"{snap['period_start']} to {snap['period_end']}")
    if snap.get("business_trading_since"):
        doc.two_col("Trading since:", snap["business_trading_since"])
    doc.two_col("Generated:", snap["generated_at"][:16].replace("T", " "))
    doc.spacer(4)
    doc.hr()
    doc.spacer(4)

    doc.text("REVENUE", bold=True, size=11)
    doc.two_col("Total revenue (period)", f"{snap['currency_code']} {float(snap['total_revenue']):,.2f}")
    if snap.get("average_monthly_revenue"):
        doc.two_col("Average monthly revenue", f"{snap['currency_code']} {float(snap['average_monthly_revenue']):,.2f}")
    doc.two_col("Months with sales activity", str(snap["active_months_in_period"]))
    doc.spacer(4)

    doc.text("PROFITABILITY", bold=True, size=11)
    doc.two_col("Gross profit (period)", f"{snap['currency_code']} {float(snap['gross_profit']):,.2f}")
    if snap.get("gross_margin_percent"):
        doc.two_col("Gross margin", f"{snap['gross_margin_percent']}%")
    doc.spacer(4)

    doc.text("RECEIVABLES & PAYABLES", bold=True, size=11)
    doc.two_col("Owed to the business (customer debt)", f"{snap['currency_code']} {float(snap['total_customer_debt_owed_to_business']):,.2f}")
    doc.two_col("Owed by the business (supplier debt)", f"{snap['currency_code']} {float(snap['total_supplier_debt_owed_by_business']):,.2f}")
    doc.two_col("Net position", f"{snap['currency_code']} {float(snap['net_receivables_position']):,.2f}", bold=True)
    doc.spacer(4)

    doc.text("CASH DISCIPLINE", bold=True, size=11)
    if snap.get("cash_discipline_percent"):
        doc.two_col("Shifts closing within expected cash", f"{snap['cash_discipline_percent']}% ({snap['shifts_evaluated']} shifts evaluated)")
    else:
        doc.text("Not enough shift data to assess.", size=9)

    if snap.get("monthly_revenue"):
        doc.spacer(6)
        doc.text("MONTHLY REVENUE", bold=True, size=11)
        rows = [[m["month"], str(m["sale_count"]), f"{float(m['revenue']):,.2f}"] for m in snap["monthly_revenue"]]
        doc.table(headers=["Month", "Sales", "Revenue"], rows=rows, col_widths=[40, 30, 50], align_right_from=1)

    if snap.get("insufficient_data_flags"):
        doc.spacer(6)
        doc.text("NOTES", bold=True, size=10)
        for flag in snap["insufficient_data_flags"]:
            doc.text(f"• {flag}", size=8.5)

    doc.spacer(8)
    doc.hr()
    doc.spacer(4)
    doc.text(
        "This is a factual summary generated directly from the business's own recorded transactions — "
        "not an audit, credit assessment, or guarantee of repayment ability.", size=7.5,
    )
    doc.text("Scan the QR code to verify this document matches what was originally generated.", size=7.5)

    # QR verification — same pattern as the sales receipt: points to a
    # public endpoint that returns the figures actually printed here,
    # not a live recomputation (see LoanReadinessReport's docstring
    # for why that distinction matters for this specific document).
    import qrcode, io
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from django.conf import settings

    qr_img = qrcode.make(f"{settings.FRONTEND_URL}/verify-loan-report/{report.id}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    qr_size = 24 * mm
    doc.check_page_break(30)
    doc.c.drawImage(ImageReader(buf), doc.MARGIN, doc.y - qr_size, qr_size, qr_size)
    doc.y -= (qr_size + 4 * mm)

    return doc.finish()
