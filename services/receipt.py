from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE = Path(__file__).resolve().parent
FONT_DIR = BASE / "fonts"
FONT_PATH = FONT_DIR / "NotoSansDevanagari-Regular.ttf"
FONT_NAME = "NotoDevanagari"

if FONT_PATH.exists():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), shapable=True))
    except Exception:
        pass

FONT = FONT_NAME if FONT_NAME in pdfmetrics.getRegisteredFontNames() else "Helvetica"
FONT_BOLD = FONT


def _text(value):
    if value is None:
        return ""
    return str(value)


def draw_receipt(c, row, org, x, y, w, h):
    c.rect(x, y, w, h)

    # Organization title
    c.setFont(FONT_BOLD, 15)
    c.drawCentredString(x + w / 2, y + h - 12 * mm, _text(org))

    c.setFont(FONT, 9.5)

    lines = [
        f"पावती क्रमांक: {_text(row.get('receipt_no'))}",
        f"दिनांक: {_text(row.get('payment_date'))}",
        f"सभासद क्रमांक: {_text(row.get('member_no'))}",
        f"नाव: {_text(row.get('name'))}",
        f"मोबाईल: {_text(row.get('mobile'))}",
        f"गाव: {_text(row.get('village'))}",
        f"तालुका: {_text(row.get('taluka'))}",
        f"प्रकार: {_text(row.get('payment_type'))}",
        f"पेमेंट पद्धत: {_text(row.get('payment_method'))}",
        f"व्यवहार क्रमांक: {_text(row.get('transaction_no'))}",
        f"रक्कम: ₹ {float(row.get('amount') or 0):,.2f}",
    ]
    if row.get("note"):
        lines.append(f"नोंद: {_text(row.get('note'))}")

    yy = y + h - 21 * mm
    for line in lines:
        c.drawString(x + 7 * mm, yy, line)
        yy -= 4 * mm

    c.line(x + 7 * mm, y + 12 * mm, x + w - 7 * mm, y + 12 * mm)
    c.setFont(FONT, 8)
    c.drawString(x + 7 * mm, y + 6 * mm, "संगणक निर्मित पावती")
    c.drawRightString(x + w - 7 * mm, y + 6 * mm, "अधिकृत स्वाक्षरी")


def make_receipt(row, org, path, copies=1):
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4

    copies = int(copies)

    if copies == 1:
        draw_receipt(c, row, org, 15 * mm, 55 * mm, W - 30 * mm, 185 * mm)
    elif copies == 2:
        h = 125 * mm
        draw_receipt(c, row, org, 10 * mm, H - 10 * mm - h, W - 20 * mm, h)
        draw_receipt(c, row, org, 10 * mm, 10 * mm, W - 20 * mm, h)
    else:
        h = 85 * mm
        draw_receipt(c, row, org, 10 * mm, H - 10 * mm - h, W - 20 * mm, h)
        draw_receipt(c, row, org, 10 * mm, H / 2 - 42 * mm, W - 20 * mm, h)
        draw_receipt(c, row, org, 10 * mm, 10 * mm, W - 20 * mm, h)

    c.save()
    return str(path)
