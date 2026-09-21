"""Receipt PDF generation. Pulls branding (logo, name, address, phone,
footer note) from the Branch/Business branding_context so every
receipt automatically reflects whatever the owner has configured —
no per-document hardcoding.
"""
import io

import qrcode
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def payment_method_display(payment) -> str:
    """Payment.method is a plain code, not a Django choices field (it
    became owner-configurable — see sales.models.PaymentMethod), so
    there's no get_method_display() anymore. Resolve the human name
    from the business's configured methods, including deactivated
    ones (a receipt for an old sale should still show what the method
    was actually called at the time, not break because it was later
    turned off). Falls back to a humanized version of the raw code if
    the method row itself is somehow gone.
    """
    from .models import PaymentMethod
    method = PaymentMethod.objects.filter(business=payment.business, code=payment.method).first()
    if method:
        return method.name
    return payment.method.replace("_", " ").title()


def generate_invoice_pdf(sale) -> bytes:
    """A formal A4 invoice for a sale — same underlying transaction as
    the thermal receipt, different document for when a customer needs
    something they can attach to their own bookkeeping (common for
    credit sales, B2B customers, or anything with tax implications).
    """
    from apps.core.pdf import DocumentPDF

    branding = sale.branch.branding_context
    doc = DocumentPDF(branding, "Invoice", sale.transaction_number)

    if sale.customer:
        doc.two_col("Bill to:", sale.customer.name, bold=True)
        if sale.customer.phone_number:
            doc.text(sale.customer.phone_number, size=8.5)
    doc.two_col("Date:", sale.created_at.strftime("%Y-%m-%d %H:%M"))
    doc.two_col("Sale type:", sale.get_sale_type_display())
    doc.spacer(4)

    items = list(sale.items.select_related("product", "unit"))
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
    doc.two_col("Subtotal", f"{sale.subtotal:,.2f}")
    if sale.discount_total:
        doc.two_col("Discount", f"-{sale.discount_total:,.2f}")
    if sale.tax_total:
        doc.two_col("Tax", f"{sale.tax_total:,.2f}")
    doc.two_col("TOTAL", f"{branding['currency_code']} {sale.grand_total:,.2f}", bold=True, size=12)

    doc.spacer(4)
    for payment in sale.payments.all():
        doc.two_col(f"Paid ({payment_method_display(payment)})", f"{payment.amount:,.2f}", size=8.5)

    return doc.finish()


def generate_receipt_pdf(sale, copy_number: int) -> bytes:
    branding = sale.branch.branding_context
    is_reprint = copy_number > 1

    buf = io.BytesIO()
    width = 80 * mm  # thermal-receipt-width layout; also prints fine on A4/letter trays
    height = (140 + len(sale.items.all()) * 8) * mm
    c = canvas.Canvas(buf, pagesize=(width, height))

    y = height - 10 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, y, branding["business_name"])
    y -= 6 * mm

    c.setFont("Helvetica", 7)
    if branding.get("address"):
        c.drawCentredString(width / 2, y, branding["address"]); y -= 4 * mm
    if branding.get("phone_number"):
        c.drawCentredString(width / 2, y, branding["phone_number"]); y -= 4 * mm
    if branding.get("header_note"):
        c.drawCentredString(width / 2, y, branding["header_note"]); y -= 4 * mm

    if is_reprint:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0.7, 0, 0)
        c.drawCentredString(width / 2, y, "*** REPRINT ***")
        c.setFillColorRGB(0, 0, 0)
        y -= 6 * mm

    y -= 2 * mm
    c.setFont("Helvetica", 7)
    c.drawString(5 * mm, y, f"Receipt: {sale.transaction_number}")
    y -= 4 * mm
    c.drawString(5 * mm, y, f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 4 * mm
    c.drawString(5 * mm, y, f"Cashier: {sale.cashier.get_full_name() or sale.cashier.email}")
    y -= 6 * mm

    c.line(5 * mm, y, width - 5 * mm, y)
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 7)
    c.drawString(5 * mm, y, "Item")
    c.drawRightString(width - 5 * mm, y, "Total")
    y -= 4 * mm
    c.setFont("Helvetica", 7)

    for item in sale.items.all():
        c.drawString(5 * mm, y, f"{item.product.name[:22]} x{item.quantity}")
        c.drawRightString(width - 5 * mm, y, f"{item.line_total:,.2f}")
        y -= 4.5 * mm

    y -= 2 * mm
    c.line(5 * mm, y, width - 5 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 7)
    c.drawString(5 * mm, y, "Subtotal"); c.drawRightString(width - 5 * mm, y, f"{sale.subtotal:,.2f}")
    y -= 4 * mm
    if sale.discount_total:
        c.drawString(5 * mm, y, "Discount"); c.drawRightString(width - 5 * mm, y, f"-{sale.discount_total:,.2f}")
        y -= 4 * mm
    if sale.tax_total:
        c.drawString(5 * mm, y, "Tax"); c.drawRightString(width - 5 * mm, y, f"{sale.tax_total:,.2f}")
        y -= 4 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(5 * mm, y, "TOTAL")
    c.drawRightString(width - 5 * mm, y, f"{branding['currency_code']} {sale.grand_total:,.2f}")
    y -= 6 * mm

    c.setFont("Helvetica", 7)
    for payment in sale.payments.all():
        c.drawString(5 * mm, y, f"Paid ({payment_method_display(payment)})")
        c.drawRightString(width - 5 * mm, y, f"{payment.amount:,.2f}")
        y -= 4 * mm

    y -= 3 * mm
    qr_img = qrcode.make(f"{settings.FRONTEND_URL}/verify/{sale.id}")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_size = 20 * mm
    c.drawImage(ImageReader(qr_buf), (width - qr_size) / 2, y - qr_size, qr_size, qr_size)
    y -= (qr_size + 4 * mm)

    if branding.get("footer_note"):
        c.setFont("Helvetica-Oblique", 7)
        c.drawCentredString(width / 2, y, branding["footer_note"])

    c.showPage()
    c.save()
    return buf.getvalue()
