from pathlib import Path
import re

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
ENGLISH_ORG_NAME = "Baliraja Shetkari Sanghatana"
ENGLISH_ORG_ADDRESS = (
    "Shop No. 21, Agricultural Produce Market Committee Complex, "
    "Kalmeshwar, Dist. Nagpur, Maharashtra - 441501"
)


def _english_value(value):
    if value is None:
        return ""
    value = str(value)
    translations = {
        "बळीराजा शेतकरी संघटना": ENGLISH_ORG_NAME,
        "शॉप नं. २१, कृषी उत्पन्न बाजार समिती कॉम्प्लेक्स, कळमेश्वर, जि. नागपूर, महाराष्ट्र–४४१५०१": ENGLISH_ORG_ADDRESS,
        "शॉप नं. २१, कृषी उत्पन्न बाजार समिती कॉम्प्लेक्स, कळमेश्वर, जि. नागपूर, महाराष्ट्र-४४१५०१": ENGLISH_ORG_ADDRESS,
        "Membership Fee": "Membership Fee", "सभासद फी": "Membership Fee",
        "Other Contribution": "Other Contribution", "इतर वर्गणी": "Other Contribution",
        "Donation": "Donation", "देणगी": "Donation",
        "Cash": "Cash", "रोख": "Cash", "UPI": "UPI",
        "Bank": "Bank Transfer", "बँक": "Bank Transfer",
        "प्रशासक": "Administrator", "कर्मचारी": "Staff",
        "admin": "Administrator", "staff": "Staff",
    }
    value = translations.get(value, value)
    devanagari_digits = str.maketrans("०१२३४५६७८९", "0123456789")
    return value.translate(devanagari_digits)


def _text(value):
    if value is None:
        return ""
    return str(value)


def _text_runs(text):
    """Yield text runs with a font that contains their glyphs."""
    for run in re.split(r"([A-Za-z]+)", str(text)):
        if run:
            yield run, "Helvetica" if run.isascii() and run.isalpha() else FONT


def _mixed_width(text, size):
    return sum(pdfmetrics.stringWidth(run, font, size)
               for run, font in _text_runs(text))


def _draw_mixed(c, x, y, text, size, align="left"):
    text = str(text)
    width = _mixed_width(text, size)
    if align == "center":
        x -= width / 2
    elif align == "right":
        x -= width
    for run, font in _text_runs(text):
        c.setFont(font, size)
        c.drawString(x, y, run)
        x += pdfmetrics.stringWidth(run, font, size)


def draw_receipt(c, row, org, x, y, w, h, address="", contact="", logo_path=None,
                 copy_label=""):
    c.rect(x, y, w, h)

    row = dict(row)
    row["payment_type"] = _english_value(row.get("payment_type"))
    row["payment_method"] = _english_value(row.get("payment_method"))
    org = _english_value(org)
    address = _english_value(address)

    # Organization identity and contact details.
    if logo_path and Path(logo_path).is_file():
        logo_size = min(17 * mm, h * 0.20)
        c.drawImage(str(logo_path), x + 6 * mm, y + h - logo_size - 3 * mm,
                    width=logo_size, height=logo_size, preserveAspectRatio=True,
                    anchor="c", mask="auto")

    _draw_mixed(c, x + w / 2, y + h - 8 * mm, _text(org), 12, "center")
    c.setFont(FONT, 7)
    address_lines = []
    if address:
        max_address_width = w - 14 * mm
        current_line = ""
        for word in _text(address).split():
            candidate = f"{current_line} {word}".strip()
            if current_line and _mixed_width(candidate, 7) > max_address_width:
                address_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            address_lines.append(current_line)
    for index, address_line in enumerate(address_lines):
        _draw_mixed(c, x + w / 2, y + h - (13 + 3 * index) * mm,
                    address_line, 7, "center")
    if contact:
        contact_y = 16 + 3 * len(address_lines)
        _draw_mixed(c, x + w / 2, y + h - contact_y * mm,
                    f"Contact: {_english_value(contact)}", 7, "center")

    lines = [
        f"Receipt No.: {_text(row.get('receipt_no'))}",
        f"Date: {_text(row.get('payment_date'))}",
        f"Member No.: {_text(row.get('member_no'))}",
        f"Name: {_text(row.get('name'))}",
        f"Mobile: {_text(row.get('mobile'))}",
        f"Village: {_text(row.get('village'))}",
        f"Taluka: {_text(row.get('taluka'))}",
        f"Type: {_text(row.get('payment_type'))}",
        f"Payment Method: {_text(row.get('payment_method'))}",
        f"Transaction No.: {_text(row.get('transaction_no'))}",
        f"Amount: INR {float(row.get('amount') or 0):,.2f}",
        f"Received By: {_text(row.get('received_by'))}",
    ]
    if row.get("note"):
        lines.append(f"Note: {_text(row.get('note'))}")

    body_top = 22 + 3 * len(address_lines)
    has_signing_panel = h >= 125 * mm
    body_font_size = 9.5 if has_signing_panel else 8
    detail_width = w - (105 * mm if has_signing_panel else 14 * mm)
    wrapped_lines = []
    for line in lines:
        current_line = ""
        for word in line.split():
            candidate = f"{current_line} {word}".strip()
            if current_line and _mixed_width(candidate, body_font_size) > detail_width:
                wrapped_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            wrapped_lines.append(current_line)

    available_body_mm = h / mm - body_top - 19
    line_gap = available_body_mm * mm / max(len(wrapped_lines), 1)
    yy = y + h - body_top * mm
    for line in wrapped_lines:
        _draw_mixed(c, x + 7 * mm, yy, line, body_font_size)
        yy -= line_gap

    if has_signing_panel:
        chair_left = x + w - 96 * mm
        chair_right = x + w - 64 * mm
        treasurer_left = x + w - 61 * mm
        treasurer_right = x + w - 29 * mm
        signature_y = y + 41 * mm
        for left, right in ((chair_left, chair_right),
                            (treasurer_left, treasurer_right)):
            c.line(left, signature_y, right, signature_y)
        _draw_mixed(c, (chair_left + chair_right) / 2, y + 35 * mm,
                    "Chairman", 6.5, "center")
        _draw_mixed(c, (chair_left + chair_right) / 2, y + 27 * mm,
                    "Pankaj Arunrao Ghonghe", 5, "center")
        _draw_mixed(c, (treasurer_left + treasurer_right) / 2, y + 35 * mm,
                    "Treasurer", 6.5, "center")
        _draw_mixed(c, (treasurer_left + treasurer_right) / 2, y + 27 * mm,
                    "Sahebrao Murlidhar Kardabhajane", 4.7, "center")
        stamp_x = x + w - 27 * mm
        stamp_y = y + 30 * mm
        c.rect(stamp_x, stamp_y, 20 * mm, 20 * mm)
        _draw_mixed(c, stamp_x + 10 * mm, stamp_y + 11 * mm,
                    "Organization", 5, "center")
        _draw_mixed(c, stamp_x + 10 * mm, stamp_y + 7 * mm,
                    "Stamp", 6, "center")

    c.line(x + 7 * mm, y + 12 * mm, x + w - 7 * mm, y + 12 * mm)
    _draw_mixed(c, x + 7 * mm, y + 6 * mm, "Computer-generated receipt", 8)
    if copy_label:
        _draw_mixed(c, x + w - 7 * mm, y + 15 * mm, copy_label, 8, "right")
    _draw_mixed(c, x + w - 7 * mm, y + 6 * mm, "Authorized Signature", 8, "right")


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
                     address, contact, logo_path, "Office Copy")
        draw_receipt(c, row, org, 10 * mm, 10 * mm, W - 20 * mm, h,
                     address, contact, logo_path, "Member Copy")
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
