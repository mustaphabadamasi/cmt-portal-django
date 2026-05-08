import os
import io
from django.conf import settings
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def get_student_photo_path(student):
    if student.photo and os.path.exists(student.photo.path):
        return student.photo.path
    return None


def generate_exam_card(student, courses, semester, session):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    center_bold = ParagraphStyle(
        'CenterBold',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        leading=12,
        fontName='Helvetica-Bold'
    )

    green_text = ParagraphStyle(
        'GreenText',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,
        leading=11,
        textColor=colors.HexColor('#1a5c38'),
        fontName='Helvetica-Bold'
    )

    red_title = ParagraphStyle(
        'RedTitle',
        parent=styles['Heading1'],
        fontSize=13,
        textColor=colors.HexColor('#c41e3a'),
        alignment=1,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        leading=13
    )

    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        leading=13
    )

    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=7,
        leading=9
    )

    story = []

    # --- HEADER WITH LOGOS ---
    logo_left = os.path.join(settings.BASE_DIR, 'static', 'images', 'cmt_logo.png')
    logo_right = os.path.join(settings.BASE_DIR, 'static', 'images', 'fud_logo.png')

    header_row = []

    # Left logo
    if os.path.exists(logo_left):
        header_row.append(Image(logo_left, width=0.7*inch, height=0.7*inch))
    else:
        header_row.append('')

    # Center text
    header_text = """
    <font size=11><b>COLLEGE OF MANAGEMENT AND TECHNOLOGY KATSINA</b></font><br/>
    <font size=8>11, Batsari Road, Day Kofar Yandaka, Katsina</font><br/>
    <font size=8>Affiliated to</font><br/>
    <font size=9 color=#1a5c38><b>Federal University Dutsin-Ma, Katsina</b></font>
    """
    header_row.append(Paragraph(header_text, center_bold))

    # Right logo
    if os.path.exists(logo_right):
        header_row.append(Image(logo_right, width=0.7*inch, height=0.7*inch))
    else:
        header_row.append('')

    header_table = Table([header_row], colWidths=[1*inch, 4.5*inch, 1*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # --- TITLE ---
    story.append(Paragraph("<b>EXAMINATION CARD</b>", red_title))

    # --- STUDENT INFO + PHOTO BOX ---
    photo_path = get_student_photo_path(student)

    # Build photo cell content
    if photo_path:
        photo_content = Image(photo_path, width=1.1*inch, height=1.3*inch)
    else:
        photo_content = Paragraph(
            "<br/><br/><br/>2x2<br/>Passport",
            ParagraphStyle('PhotoBox', parent=styles['Normal'], alignment=1, fontSize=9)
        )

    info_data = [
        [
            Paragraph("<b>Name:</b>", label_style),
            Paragraph(student.user.get_full_name(), value_style),
            Paragraph("<b>Level:</b>", label_style),
            Paragraph(student.level, value_style),
            photo_content
        ],
        [
            Paragraph("<b>Matric. No:</b>", label_style),
            Paragraph(student.matric_number, value_style),
            Paragraph("<b>Session:</b>", label_style),
            Paragraph(session, value_style),
            ''
        ],
        [
            Paragraph("<b>Programme:</b>", label_style),
            Paragraph(str(student.programme) if student.programme else 'N/A', value_style),
            Paragraph("<b>Semester:</b>", label_style),
            Paragraph(str(semester), value_style),
            ''
        ],
    ]

    info_table = Table(
        info_data,
        colWidths=[1.0*inch, 2.5*inch, 1.0*inch, 1.3*inch, 1.2*inch]
    )
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (3, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (3, 2), 0.5, colors.black),
        ('BOX', (4, 0), (4, 2), 0.5, colors.black),
        ('SPAN', (4, 0), (4, 2)),
        ('ALIGN', (4, 0), (4, 2), 'CENTER'),
        ('VALIGN', (4, 0), (4, 2), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # --- COURSES TABLE ---
    story.append(Paragraph(
        "<b>COURSE(S) REGISTERED</b>",
        ParagraphStyle(
            'CourseHeader',
            parent=styles['Normal'],
            alignment=1,
            fontSize=10,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
    ))

    course_data = [['S/N', 'Course Code', 'Course Title', "Invigilator's Signature", 'Date']]

    for idx, c in enumerate(courses, 1):
        course_data.append([
            str(idx),
            getattr(c, 'code', ''),
            getattr(c, 'title', ''),
            '',
            ''
        ])

    # Pad with empty rows if less than 6 for better layout
    while len(course_data) < 7:
        course_data.append([str(len(course_data)), '', '', '', ''])

    course_table = Table(
        course_data,
        colWidths=[0.5*inch, 1.1*inch, 2.8*inch, 1.5*inch, 0.8*inch]
    )
    course_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5c38')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(course_table)
    story.append(Spacer(1, 14))

    # --- SIGNATURES ---
    sig_data = [
        [Paragraph("<b>Student's Sign & Date:</b>", label_style), '_______________________________'],
        ['', ''],
        [Paragraph("<b>HOD's Sign & Date:</b>", label_style), '_______________________________'],
    ]
    sig_table = Table(sig_data, colWidths=[1.8*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 10))

    # --- REGISTRAR LINE ---
    reg_data = [[
        Paragraph("<b>EC53405099</b>", ParagraphStyle('Barcode', parent=styles['Normal'], fontSize=9)),
        Paragraph("<b>Registrar's Sign, Date & Stamp:</b>", label_style),
        '_______________________________'
    ]]
    reg_table = Table(reg_data, colWidths=[1.2*inch, 2.3*inch, 2.5*inch])
    reg_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(reg_table)
    story.append(Spacer(1, 18))

    # --- EXAMINATION REGULATIONS ---
    story.append(Paragraph(
        "<b>EXAMINATION REGULATIONS</b>",
        ParagraphStyle(
            'RegTitle',
            parent=styles['Normal'],
            alignment=1,
            fontSize=10,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
    ))

    regulations = [
        "1. Student shall be at the examination room at least fifteen (15) minutes before the time appointed for the commencement of the examination. Candidates should, therefore, refrain from studying in halls earmarked for examinations.",
        "2. Student must NOT take into the examination hall any programmed electronic device, handbag, book, paper, or any other form of printed or written material, hand bags and brief cases.",
        "3. Student must bring his/her examination and college ID card to the examination hall and display them on his/her desk.",
        "4. While the examination is in progress, communication between candidates is strictly forbidden, and any candidate found to be giving or receiving irregular assistance may be required to withdraw from the examination.",
        "5. Student must sign in the attendance form with his/her Reg. number and must sign out same on submission of their script.",
        "6. Student must correctly fill in all the spaces provided on the cover of the answer booklet and all additional sheets of paper issued during the examination.",
        "7. No candidate will be permitted to: (i) Enter examination room 30 minutes after the commencement of the examination (ii) Leave the examination room before the first 45 minutes of the examination (iii) Write examination without college ID Card.",
        "8. Examination answer scripts/booklets whether used or unused should not be taken out of the examination hall by students.",
        "9. A student involved in examination misconduct or malpractice may be expelled from the College.",
        "10. Candidates must adhere strictly to the sitting arrangement made by the Chief Invigilator."
    ]

    for reg in regulations:
        story.append(Paragraph(
            reg,
            ParagraphStyle(
                'RegText',
                parent=small_style,
                fontSize=7,
                leading=9,
                leftIndent=12,
                rightIndent=12,
                spaceAfter=3,
                alignment=0
            )
        ))

    doc.build(story)
    buffer.seek(0)
    return buffer