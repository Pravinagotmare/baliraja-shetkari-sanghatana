import pandas as pd
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from db import query
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

FONT_PATH = Path(__file__).resolve().parent / "services" / "fonts" / "NotoSansDevanagari-Regular.ttf"
FONT_NAME = "BalirajaDevanagari"
if FONT_PATH.exists() and FONT_NAME not in pdfmetrics.getRegisteredFontNames():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH), shapable=True))
    except Exception:
        pass


def printable_pdf(title, columns, rows, landscape_page=False, column_widths=None):
    output = BytesIO()
    page_size = landscape(A4) if landscape_page else A4
    doc = SimpleDocTemplate(output, pagesize=page_size, rightMargin=12*mm,
                            leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    font = FONT_NAME if FONT_NAME in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName=font,
                                 fontSize=15, leading=20, alignment=TA_CENTER,
                                 shaping=True)
    cell_style = ParagraphStyle("Cell", parent=styles["BodyText"], fontName=font,
                                fontSize=7, leading=9, wordWrap="CJK",
                                shaping=True)
    data = [[Paragraph(escape(str(value)), cell_style) for value in columns]]
    data.extend([[Paragraph(escape("" if value is None else str(value)), cell_style) for value in row]
                 for row in rows])
    available_width = page_size[0] - 24*mm
    widths = ([available_width * fraction for fraction in column_widths]
              if column_widths else [available_width / len(columns)] * len(columns))
    table = Table(data, repeatRows=1, colWidths=widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4f1e1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#243329")),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#9aa79b")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    doc.build([Paragraph(title, title_style), Spacer(1, 5*mm), table])
    return output.getvalue()


def member_payments_report():
    return query('''SELECT m.member_no,m.name,m.mobile,v.name AS village,
        p.receipt_no,p.payment_type,p.amount,p.payment_method,p.payment_date
        FROM members m
        LEFT JOIN villages v ON v.id=m.village_id
        LEFT JOIN payments p ON p.member_id=m.id
        ORDER BY m.id DESC,p.payment_date,p.id''')

def members_report():
    return pd.DataFrame(query(
        '''SELECT m.member_no,m.name,m.mobile,
        v.name AS village,t.name AS taluka,
        m.address,m.registration_date
        FROM members m
        LEFT JOIN villages v ON v.id=m.village_id
        LEFT JOIN talukas t ON t.id=v.taluka_id
        ORDER BY m.id DESC'''
    ))

def payments_report():
    return pd.DataFrame(query(
        '''SELECT p.receipt_no,m.member_no,m.name,m.mobile,
        v.name AS village,t.name AS taluka,
        p.payment_type,p.amount,p.payment_method,
        p.transaction_no,p.payment_date,p.note
        FROM payments p
        JOIN members m ON m.id=p.member_id
        LEFT JOIN villages v ON v.id=m.village_id
        LEFT JOIN talukas t ON t.id=v.taluka_id
        ORDER BY p.id DESC'''
    ))

def excel_report():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        members_report().to_excel(
            writer, index=False, sheet_name="Members"
        )

        payments_report().to_excel(
            writer, index=False, sheet_name="Payments"
        )

        p = payments_report()

        if not p.empty:
            p.groupby("payment_type")["amount"].sum().reset_index().to_excel(
                writer, index=False, sheet_name="Summary"
            )

            p.groupby(
                ["taluka","village"]
            )["amount"].sum().reset_index().to_excel(
                writer, index=False, sheet_name="Village Collection"
            )

    return output.getvalue()
