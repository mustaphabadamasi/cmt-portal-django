
import hashlib, os
from io import BytesIO
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.barcode import code128

CMT_LOGO_PATH   = os.path.join(settings.BASE_DIR, "static", "images", "cmt_logo.png.png")
FUDMA_LOGO_PATH = os.path.join(settings.BASE_DIR, "static", "images", "fudma_logo.png_optimized_250.png")

GREEN  = colors.HexColor("#1a5c38")
GOLD   = colors.HexColor("#c8881a")
LGRAY  = colors.HexColor("#f0f4f0")
DGRAY  = colors.HexColor("#4a5568")
WHITE  = colors.white
BLACK  = colors.black
LGREEN = colors.HexColor("#e8f5e0")

W, H = A4   # 595 x 842 pt

def generate_receipt_pdf(payment):
    """Generate professional receipt PDF using ReportLab"""
    buf = BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    
    # ── Security hash ───────────────────────────────────────
    raw = f"{payment.reference}{payment.student.reg_number}{payment.amount}{payment.receipt_no}"
    sec_hash = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    verify_code = f"CMT-{sec_hash[:4]}-{sec_hash[4:8]}-{sec_hash[8:12]}-{sec_hash[12:16]}"

    # ══ SECURITY WATERMARK ══════════════════════════════════
    c.saveState()
    c.setFillColor(colors.HexColor("#1a5c38"))
    c.setFillAlpha(0.04)
    c.setFont("Helvetica-Bold", 72)
    c.translate(W/2, H/2)
    c.rotate(45)
    c.drawCentredString(0, 40,  "OFFICIAL")
    c.drawCentredString(0, -60, "OFFICIAL")
    c.restoreState()

    # ══ SECURITY BORDER PATTERN ═════════════════════════════
    # Outer border
    c.setStrokeColor(GREEN)
    c.setLineWidth(3)
    c.rect(10*mm, 10*mm, W-20*mm, H-20*mm)
    # Inner thin border
    c.setLineWidth(0.5)
    c.setStrokeColor(GOLD)
    c.rect(12*mm, 12*mm, W-24*mm, H-24*mm)
    # Corner decorations
    for x, y in [(14*mm, H-14*mm), (W-14*mm, H-14*mm), (14*mm, 14*mm), (W-14*mm, 14*mm)]:
        c.setFillColor(GOLD)
        c.circle(x, y, 2*mm, fill=1)

    # ══ HEADER BAND ═════════════════════════════════════════
    c.setFillColor(GREEN)
    c.rect(10*mm, H-42*mm, W-20*mm, 30*mm, fill=1, stroke=0)

    # Logos
    try:
        c.drawImage(CMT_LOGO_PATH,  15*mm, H-41*mm, width=24*mm, height=28*mm, preserveAspectRatio=True, mask="auto")
        c.drawImage(FUDMA_LOGO_PATH, W-39*mm, H-41*mm, width=24*mm, height=28*mm, preserveAspectRatio=True, mask="auto")
    except:
        pass

    # School name in header
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W/2, H-24*mm, "COLLEGE OF MANAGEMENT AND TECHNOLOGY")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, H-30*mm, "KATSINA")
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W/2, H-35*mm, "Affiliated to Federal University Dutsin-Ma  |  11, Batsari Road, Day Kofar Yandaka, Katsina")

    # ══ TITLE BAR ═══════════════════════════════════════════
    c.setFillColor(GOLD)
    c.rect(10*mm, H-50*mm, W-20*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, H-46.5*mm, "OFFICIAL PAYMENT RECEIPT")

    # ══ REFERENCE BOX + PASSPORT ════════════════════════════
    y_start = H - 63*mm
    c.setFillColor(LGREEN)
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.8)
    c.roundRect(15*mm, y_start, 120*mm, 16*mm, 3*mm, fill=1, stroke=1)

    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(19*mm, y_start+10*mm, f"Transaction ID: {payment.reference}")
    c.setFillColor(DGRAY)
    c.setFont("Helvetica", 8)
    c.drawString(19*mm, y_start+4.5*mm, f"Receipt No: {payment.receipt_no}")

    # Passport photo or box
    px, py, pw, ph = W-45*mm, y_start-12*mm, 28*mm, 33*mm
    c.setStrokeColor(DGRAY)
    c.setLineWidth(0.5)
    c.rect(px, py, pw, ph)
    photo_path = payment.student.photo.path if payment.student.photo else None
    if photo_path and os.path.exists(photo_path):
        try:
            c.drawImage(photo_path, px, py, pw, ph, preserveAspectRatio=True, mask="auto")
        except:
            pass
    else:
        c.setFillColor(LGRAY)
        c.rect(px, py, pw, ph, fill=1, stroke=0)
        c.setFillColor(DGRAY)
        c.setFont("Helvetica", 7)
        c.drawCentredString(px+pw/2, py+ph/2+2*mm, "2x2")
        c.drawCentredString(px+pw/2, py+ph/2-2*mm, "Passport")

    # ══ AMOUNT BOX ══════════════════════════════════════════
    ya = y_start - 4*mm
    c.setFillColor(GREEN)
    c.roundRect(15*mm, ya-16*mm, 113*mm, 16*mm, 3*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(71.5*mm, ya-5.5*mm, "AMOUNT PAID")
    c.setFont("Helvetica-Bold", 18)
    amount_str = f"NGN {payment.amount:,.0f}"
    c.drawCentredString(71.5*mm, ya-12.5*mm, amount_str)

    # ══ DETAILS TABLE ═══════════════════════════════════════
    yd = ya - 22*mm
    rows = [
        ("Student Name",   payment.student.user.get_full_name()),
        ("Matric Number",  payment.student.reg_number),
        ("Programme",      payment.student.programme.name if payment.student.programme else ""),
        ("Payment Type",   f"{payment.get_payment_type_display()} School Fees"),
        ("Session",        str(payment.session) if payment.session else ""),
        ("Payment Status", "✓  PAID"),
        ("Date Approved",  payment.approved_at.strftime("%d %B %Y, %I:%M %p") if payment.approved_at else ""),
        ("Approved By",    payment.approved_by.get_full_name() if payment.approved_by else "CMT Registrar"),
    ]

    row_h = 8*mm
    col1_w = 45*mm
    col2_w = 110*mm
    col1_x = 15*mm
    col2_x = col1_x + col1_w

    for i, (label, value) in enumerate(rows):
        y_row = yd - i * row_h
        # Alternating background
        if i % 2 == 0:
            c.setFillColor(LGRAY)
            c.rect(col1_x, y_row - 1.5*mm, col1_w + col2_w, row_h, fill=1, stroke=0)
        # Label
        c.setFillColor(DGRAY)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(col1_x + 2*mm, y_row + 2*mm, label + ":")
        # Value
        c.setFillColor(BLACK)
        c.setFont("Helvetica", 8.5)
        if label == "Payment Status":
            c.setFillColor(GREEN)
            c.setFont("Helvetica-Bold", 8.5)
        c.drawString(col2_x + 2*mm, y_row + 2*mm, str(value))
        # Thin row divider
        c.setStrokeColor(colors.HexColor("#d1d5db"))
        c.setLineWidth(0.3)
        c.line(col1_x, y_row - 1.5*mm, col1_x + col1_w + col2_w, y_row - 1.5*mm)

    # Outer table border
    table_h = len(rows) * row_h
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.8)
    c.rect(col1_x, yd - table_h + row_h - 1.5*mm, col1_w + col2_w, table_h)
    # Column divider
    c.setLineWidth(0.5)
    c.line(col2_x, yd - table_h + row_h - 1.5*mm, col2_x, yd + row_h - 1.5*mm)

    # ══ BARCODE ═════════════════════════════════════════════
    yb = yd - table_h - 10*mm
    try:
        bc = code128.Code128(payment.reference, barHeight=12*mm, barWidth=0.5, humanReadable=True)
        bc.drawOn(c, W/2 - bc.width/2, yb)
    except:
        pass

    # ══ SECURITY STRIP ══════════════════════════════════════
    ys = 28*mm
    c.setFillColor(GREEN)
    c.rect(10*mm, ys, W-20*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(W/2, ys+2.5*mm, f"SECURITY CODE: {verify_code}  |  Verify at: mustapher001.pythonanywhere.com/verify/")

    # ══ FOOTER ══════════════════════════════════════════════
    c.setFillColor(DGRAY)
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(W/2, 21*mm, "This receipt is computer-generated and is valid without a physical stamp or signature.")
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#9ca3af"))
    c.drawCentredString(W/2, 17*mm, f"Printed: {datetime.now().strftime('%d %B %Y at %I:%M %p')}  |  CMT Academic Portal  |  Document ID: {sec_hash[:8]}")

    c.save()
    buf.seek(0)
    return buf.getvalue()
