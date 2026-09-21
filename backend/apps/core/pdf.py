"""Shared A4 document rendering — the letterhead, title block, and
table helpers every generated business document (invoice, quotation,
proforma invoice, purchase order, goods-received report, shift-closing
report, supplier statement) is built from, so they all look like they
belong to the same business and the same app, and a branding change
in one place (Business.branding_context) updates every document type
at once rather than needing N separate fixes.

This is deliberately a different renderer from apps.sales.documents,
which produces an 80mm thermal-receipt layout — these are proper A4
documents meant to be printed on letterhead or emailed as PDFs.
"""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


class DocumentPDF:
    """A small stateful wrapper around reportlab's canvas that
    handles the letterhead, running y-position, and page breaks, so
    each document generator function only has to describe its own
    content."""

    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 18 * mm

    def __init__(self, branding: dict, title: str, document_number: str = ""):
        self.branding = branding
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=A4)
        self.y = self.PAGE_HEIGHT - self.MARGIN
        self._draw_letterhead(title, document_number)

    def _draw_letterhead(self, title, document_number):
        c, y = self.c, self.y
        c.setFont("Helvetica-Bold", 16)
        c.drawString(self.MARGIN, y, self.branding["business_name"])
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        for line in filter(None, [self.branding.get("address"), self.branding.get("phone_number"), self.branding.get("email")]):
            c.drawString(self.MARGIN, y, line)
            y -= 4.5 * mm

        # Title block, right-aligned
        right_x = self.PAGE_WIDTH - self.MARGIN
        title_y = self.PAGE_HEIGHT - self.MARGIN
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(right_x, title_y, title.upper())
        if document_number:
            c.setFont("Helvetica", 9)
            c.drawRightString(right_x, title_y - 6 * mm, document_number)

        y -= 4 * mm
        c.line(self.MARGIN, y, right_x, y)
        y -= 8 * mm
        self.y = y

    def text(self, text, size=9, bold=False, gap=4.5):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(self.MARGIN, self.y, text)
        self.y -= gap * mm

    def two_col(self, left, right, size=9, bold=False, gap=4.5):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(self.MARGIN, self.y, left)
        self.c.drawRightString(self.PAGE_WIDTH - self.MARGIN, self.y, right)
        self.y -= gap * mm

    def hr(self, gap=4):
        self.c.line(self.MARGIN, self.y, self.PAGE_WIDTH - self.MARGIN, self.y)
        self.y -= gap * mm

    def spacer(self, mm_amount=4):
        self.y -= mm_amount * mm

    def check_page_break(self, needed_mm=20):
        if self.y < self.MARGIN + needed_mm * mm:
            self.c.showPage()
            self.y = self.PAGE_HEIGHT - self.MARGIN

    def table(self, headers, rows, col_widths, align_right_from=1):
        """headers: list[str]; rows: list[list[str]]; col_widths in mm,
        must sum to <= usable page width."""
        x_positions = []
        x = self.MARGIN
        for w in col_widths:
            x_positions.append(x)
            x += w * mm

        self.check_page_break(12)
        self.c.setFont("Helvetica-Bold", 8.5)
        for i, h in enumerate(headers):
            if i >= align_right_from:
                self.c.drawRightString(x_positions[i] + col_widths[i] * mm, self.y, h)
            else:
                self.c.drawString(x_positions[i], self.y, h)
        self.y -= 4 * mm
        self.hr(gap=3)

        self.c.setFont("Helvetica", 8.5)
        for row in rows:
            self.check_page_break(6)
            for i, cell in enumerate(row):
                if i >= align_right_from:
                    self.c.drawRightString(x_positions[i] + col_widths[i] * mm, self.y, str(cell))
                else:
                    self.c.drawString(x_positions[i], self.y, str(cell)[:60])
            self.y -= 4.5 * mm

    def footer_note(self):
        note = self.branding.get("footer_note")
        if note:
            self.check_page_break(10)
            self.c.setFont("Helvetica-Oblique", 8)
            self.c.drawCentredString(self.PAGE_WIDTH / 2, self.MARGIN / 2, note)

    def finish(self) -> bytes:
        self.footer_note()
        self.c.showPage()
        self.c.save()
        return self.buf.getvalue()
