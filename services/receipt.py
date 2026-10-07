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


def draw_receipt(c, row, org, x, y, w, h, address="", contact="", logo_path=None,
                 copy_label=""):
    c.rect(x, y, w, h)

    # Organization identity and contact details.
    if logo_path and Path(logo_path).is_file():
        logo_size = min(17 * mm, h * 0.20)
        c.drawImage(str(logo_path), x + 6 * mm, y + h - logo_size - 3 * mm,
                    width=logo_size, height=logo_size, preserveAspectRatio=True,
                    anchor="c", mask="auto")

    c.setFont(FONT_BOLD, 12)
    c.drawCentredString(x + w / 2, y + h - 8 * mm, _text(org))
    c.setFont(FONT, 7)
    address_lines = []
    if address:
        max_address_width = w - 14 * mm
        current_line = ""
        for word in _text(address).split():
            candidate = f"{current_line} {word}".strip()
            if current_line and c.stringWidth(candidate, FONT, 7) > max_address_width:
                address_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            address_lines.append(current_line)
    for index, address_line in enumerate(address_lines):
        c.drawCentredString(x + w / 2, y + h - (13 + 3 * index) * mm, address_line)
    if contact:
        contact_y = 16 + 3 * len(address_lines)
        c.drawCentredString(x + w / 2, y + h - contact_y * mm, f"संपर्क: {_text(contact)}")

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
        f"रक्कम स्वीकारणारे: {_text(row.get('received_by'))} — {_text(row.get('receiver_role'))}",
    ]
    if row.get("note"):
        lines.append(f"नोंद: {_text(row.get('note'))}")

    body_top = 22 + 3 * len(address_lines)
    has_signing_panel = h >= 125 * mm
    body_font_size = 9.5 if has_signing_panel else 8
    detail_width = w - (98 * mm if has_signing_panel else 14 * mm)
    wrapped_lines = []
    for line in lines:
        current_line = ""
        for word in line.split():
            candidate = f"{current_line} {word}".strip()
            if current_line and c.stringWidth(candidate, FONT, body_font_size) > detail_width:
                wrapped_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            wrapped_lines.append(current_line)

    available_body_mm = h / mm - body_top - 19
    line_gap = available_body_mm * mm / max(len(wrapped_lines), 1)
    c.setFont(FONT, body_font_size)
    yy = y + h - body_top * mm
    for line in wrapped_lines:
        c.drawString(x + 7 * mm, yy, line)
        yy -= line_gap

    if has_signing_panel:
        signature_left = x + w - 79 * mm
        signature_right = x + w - 31 * mm
        c.setFont(FONT, 7.5)
        c.line(signature_left, y + 57 * mm, signature_right, y + 57 * mm)
        c.drawRightString(signature_right, y + 50 * mm, "अध्यक्ष")
        c.drawRightString(signature_right, y + 44 * mm, "पंकज अरुणराव घोंगे")
        c.line(signature_left, y + 31 * mm, signature_right, y + 31 * mm)
        c.drawRightString(signature_right, y + 24 * mm, "कोषाध्यक्ष")
        c.drawRightString(signature_right, y + 18 * mm, "साहेबराव मुरलीधर करडभाजणे")
        stamp_x = x + w - 27 * mm
        stamp_y = y + 34 * mm
        c.rect(stamp_x, stamp_y, 20 * mm, 20 * mm)
        c.setFont(FONT, 7)
        c.drawCentredString(stamp_x + 10 * mm, stamp_y + 9 * mm, "शिक्का")

    c.line(x + 7 * mm, y + 12 * mm, x + w - 7 * mm, y + 12 * mm)
    c.setFont(FONT, 8)
    c.drawString(x + 7 * mm, y + 6 * mm, "संगणक निर्मित पावती")
    if copy_label:
        c.drawRightString(x + w - 7 * mm, y + 15 * mm, copy_label)
    c.drawRightString(x + w - 7 * mm, y + 6 * mm, "अधिकृत स्वाक्षरी")


def make_receipt(row, org, path, copies=1, address="", contact="", logo_path=None):
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4

    copies = int(copies)

    if copies == 1:
        draw_receipt(c, row, org, 15 * mm, 55 * mm, W - 30 * mm, 185 * mm,
                     address, contact, logo_path)
    elif copies == 2:
        h = (H - 20 * mm) / 2
        draw_receipt(c, row, org, 10 * mm, H - 10 * mm - h, W - 20 * mm, h,
                     address, contact, logo_path, "ऑफिस कॉपी / Office Copy")
        draw_receipt(c, row, org, 10 * mm, 10 * mm, W - 20 * mm, h,
                     address, contact, logo_path, "सभासद कॉपी / Member Copy")
    else:
        h = 85 * mm
        draw_receipt(c, row, org, 10 * mm, H - 10 * mm - h, W - 20 * mm, h,
                     address, contact, logo_path)
        draw_receipt(c, row, org, 10 * mm, H / 2 - 42 * mm, W - 20 * mm, h,
                     address, contact, logo_path)
        draw_receipt(c, row, org, 10 * mm, 10 * mm, W - 20 * mm, h,
                     address, contact, logo_path)

    c.save()
    return str(path)
