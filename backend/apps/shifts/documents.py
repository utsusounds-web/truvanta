"""Shift-closing report (spec section 10) — a printable/emailable
record of a single cash-handling session: opening float, sales during
the shift, expected vs. physically counted closing cash, and the
resulting variance. Meant to be handed to an employee as their copy
after closing, or filed for a dispute.
"""
from apps.core.pdf import DocumentPDF


def generate_shift_closing_pdf(shift) -> bytes:
    branding = shift.branch.branding_context
    doc = DocumentPDF(branding, "Shift Closing Report", f"Shift #{str(shift.id)[:8]}")

    doc.two_col("Employee:", shift.employee.get_full_name() or shift.employee.email, bold=True)
    doc.two_col("Branch:", shift.branch.name)
    doc.two_col("Opened:", shift.opened_at.strftime("%Y-%m-%d %H:%M"))
    if shift.closed_at:
        doc.two_col("Closed:", shift.closed_at.strftime("%Y-%m-%d %H:%M"))
    doc.spacer(4)
    doc.hr()
    doc.spacer(2)

    doc.two_col("Opening cash", f"{shift.opening_cash:,.2f}")
    if shift.expected_closing_cash is not None:
        doc.two_col("Expected closing cash", f"{shift.expected_closing_cash:,.2f}")
    if shift.closing_physical_cash is not None:
        doc.two_col("Physical cash counted", f"{shift.closing_physical_cash:,.2f}")
    if shift.variance is not None:
        doc.spacer(2)
        doc.hr()
        doc.spacer(2)
        variance_label = "Cash Over" if shift.variance > 0 else "Cash Short" if shift.variance < 0 else "Balanced"
        doc.two_col(f"Variance ({variance_label})", f"{shift.variance:,.2f}", bold=True, size=11)

    if shift.status == "reviewed":
        doc.spacer(6)
        doc.text(f"Reviewed by {shift.reviewed_by.get_full_name() or shift.reviewed_by.email}" if shift.reviewed_by else "Reviewed", size=8.5)
        if shift.review_note:
            doc.text(f"Note: {shift.review_note}", size=8.5)
    elif shift.status == "pending_review":
        doc.spacer(6)
        doc.text("Status: Pending owner/admin review.", size=9, bold=True)

    return doc.finish()
