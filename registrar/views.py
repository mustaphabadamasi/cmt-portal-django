from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from core.models import Session, Semester
from academics.models import Programme, Course, CourseOutline
from fees.models import Payment
from students.models import Student

try:
    from academics.models import CourseRegistration
except ImportError:
    CourseRegistration = None


@login_required
def dashboard(request):
    active_session   = Session.objects.filter(is_active=True).first()
    active_semester  = Semester.objects.filter(is_active=True).first()
    total_students   = Student.objects.count()
    pending_payments = Payment.objects.filter(status="pending").count()
    approved_payments= Payment.objects.filter(status="approved").count()
    missing_photos   = Student.objects.filter(photo="").count()
    outlines_count   = CourseOutline.objects.filter(is_active=True).count()
    context = {
        "active_session": active_session, "active_semester": active_semester,
        "total_students": total_students, "pending_payments": pending_payments,
        "approved_payments": approved_payments, "missing_photos": missing_photos,
        "outlines_count": outlines_count,
    }
    return render(request, "registrar/dashboard.html", context)


@login_required
def students(request):
    all_students = Student.objects.select_related("user","programme").all().order_by("reg_number")
    programmes = Programme.objects.all()
    return render(request, "registrar/students.html", {"students": all_students, "programmes": programmes})


@login_required
def fees(request):
    status   = request.GET.get("status","pending")
    payments = Payment.objects.filter(status=status).select_related("student__user","session","semester").order_by("-created_at")
    context  = {"payments": payments, "status": status,
                "pending_count":  Payment.objects.filter(status="pending").count(),
                "approved_count": Payment.objects.filter(status="approved").count(),
                "rejected_count": Payment.objects.filter(status="rejected").count()}
    return render(request, "registrar/fees.html", context)


@login_required
def approve_payment(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)
    action  = request.POST.get("action")
    if action == "approve":
        payment.status      = "approved"
        payment.approved_by = request.user
        payment.approved_at = timezone.now()
        payment.receipt_no  = f"CMT-{payment.pk:05d}"
        payment.save()
        messages.success(request, f"Payment approved. Receipt: {payment.receipt_no}")
    elif action == "reject":
        payment.status = "rejected"
        payment.note   = request.POST.get("note","")
        payment.save()
        messages.warning(request, "Payment rejected.")
    return redirect("registrar_fees")


@login_required
def payment_receipt(request, payment_id):
    from students.receipt_generator import generate_receipt_pdf
    payment = get_object_or_404(Payment, pk=payment_id, status="approved")
    pdf     = generate_receipt_pdf(payment)
    fname   = f"Receipt_{payment.receipt_no}_{payment.student.reg_number.replace('/', '_')}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'filename="{fname}"'
    return response


@login_required
def documents(request):
    students = Student.objects.select_related("user","programme").all()
    return render(request, "registrar/documents.html", {"students": students})


@login_required
def photo(request):
    student = None
    reg = request.GET.get("reg","").strip()
    if reg:
        try:
            student = Student.objects.select_related("user","programme").get(reg_number=reg)
        except Student.DoesNotExist:
            messages.error(request, f"No student found with reg number: {reg}")
    return render(request, "registrar/photo.html", {"student": student})


@login_required
def save_photo(request):
    import base64, uuid
    from django.core.files.base import ContentFile
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        student    = get_object_or_404(Student, pk=student_id)
        photo_data = request.POST.get("photo_data","")
        photo_file = request.FILES.get("photo_file")
        if photo_data and photo_data.startswith("data:image"):
            img_data = photo_data.split(",")[1]
            img = ContentFile(base64.b64decode(img_data), name=f"{uuid.uuid4()}.jpg")
            student.photo.save(img.name, img)
            messages.success(request, "Webcam photo saved!")
        elif photo_file:
            student.photo = photo_file
            student.save()
            messages.success(request, "Photo uploaded!")
        return redirect(f"/registrar/photo/?reg={student.reg_number}")
    return redirect("registrar_photo")


@login_required
def academic_config(request):
    sessions = Session.objects.prefetch_related("semesters").all()
    return render(request, "registrar/academic_config.html", {"sessions": sessions})


@login_required
def create_session(request):
    if request.method == "POST":
        name       = request.POST.get("name","").strip()
        is_active  = request.POST.get("is_active") == "on"
        start_date = request.POST.get("start_date") or None
        end_date   = request.POST.get("end_date")   or None
        if not name:
            messages.error(request, "Session name is required.")
            return redirect("academic_config")
        if Session.objects.filter(name=name).exists():
            messages.error(request, f"Session {name} already exists.")
            return redirect("academic_config")
        session = Session.objects.create(name=name, is_active=is_active,
                                          start_date=start_date, end_date=end_date)
        Semester.objects.create(session=session, name="First Semester")
        Semester.objects.create(session=session, name="Second Semester")
        messages.success(request, f"Session {name} created with both semesters.")
    return redirect("academic_config")


@login_required
def toggle_session(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    session.is_active = not session.is_active
    session.save()
    messages.success(request, f"Session {session.name} updated.")
    return redirect("academic_config")


@login_required
def toggle_semester(request, semester_id):
    semester = get_object_or_404(Semester, pk=semester_id)
    action   = request.POST.get("action")
    if action == "activate":     semester.is_active = True
    elif action == "deactivate": semester.is_active = False
    elif action == "open_reg":   semester.reg_open  = True
    elif action == "close_reg":  semester.reg_open  = False
    semester.save()
    messages.success(request, f"{semester} updated.")
    return redirect("academic_config")


# ─────────────────────────────────────────────────────────
# COURSE STRUCTURE — LIST + CREATE
# ─────────────────────────────────────────────────────────
@login_required
def course_structure(request):
    outlines   = CourseOutline.objects.select_related("programme","semester__session").all()
    semesters  = Semester.objects.select_related("session").all()
    programmes = Programme.objects.all()
    context    = {"outlines": outlines, "semesters": semesters, "programmes": programmes}
    return render(request, "registrar/course_structure.html", context)


@login_required
def create_outline(request):
    if request.method == "POST":
        name       = request.POST.get("name","").strip()
        prog_id    = request.POST.get("programme")
        level      = request.POST.get("level")
        sem_id     = request.POST.get("semester")
        min_units  = int(request.POST.get("min_units", 15))
        max_units  = int(request.POST.get("max_units", 24))

        if not name:
            messages.error(request, "Outline name is required.")
            return redirect("course_structure")

        programme = get_object_or_404(Programme, pk=prog_id)
        semester  = get_object_or_404(Semester, pk=sem_id)

        outline, created = CourseOutline.objects.get_or_create(
            programme=programme, programme__level=level, semester=semester,
            defaults={"name": name, "min_units": min_units, "max_units": max_units}
        )
        if not created:
            outline.name      = name
            outline.min_units = min_units
            outline.max_units = max_units
            outline.save()

        messages.success(request, f"Outline '{name}' created. Now assign courses to it.")
        return redirect("edit_outline", outline_id=outline.pk)

    return redirect("course_structure")


@login_required
def edit_outline(request, outline_id):
    outline  = get_object_or_404(CourseOutline, pk=outline_id)
    courses  = Course.objects.all().order_by("code").distinct()
    
    # Carryover detection for Diploma II
    carryover_students = []
    if outline.level == "Diploma II" and CourseRegistration:
        # Students in this programme/level who have failed courses
        carryover_students = Student.objects.filter(
            programme=outline.programme,
            programme__level=outline.level,
            course_registrations__status="failed"
        ).distinct().prefetch_related(
            "course_registrations__course"
        ).select_related("user")

    if request.method == "POST":
        course_ids = request.POST.getlist("courses")
        outline.courses.set(course_ids)
        messages.success(request, f"Courses saved for '{outline.name}'. Total: {outline.total_units()} units.")
        return redirect("edit_outline", outline_id=outline.pk)

    context = {
        "outline": outline,
        "courses": courses,
        "carryover_students": carryover_students,
        "assigned_ids": list(outline.courses.values_list("pk", flat=True)),
    }
    return render(request, "registrar/edit_outline.html", context)


@login_required
def delete_outline(request, outline_id):
    outline = get_object_or_404(CourseOutline, pk=outline_id)
    name    = outline.name
    outline.delete()
    messages.success(request, f"Outline '{name}' deleted.")
    return redirect("course_structure")


@login_required
def add_student(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if request.method == "POST":
        first_name  = request.POST.get("first_name","").strip().title()
        last_name   = request.POST.get("last_name","").strip().title()
        reg_number  = request.POST.get("reg_number","").strip()
        programme_id= request.POST.get("programme")
        status      = request.POST.get("status","Active")

        if Student.objects.filter(reg_number=reg_number).exists():
            messages.error(request, f"Student with reg number {reg_number} already exists.")
            return redirect("registrar_students")

        username = reg_number.replace("/","").upper()
        if User.objects.filter(username=username).exists():
            username += "X"

        programme = get_object_or_404(Programme, pk=programme_id)
        session   = Session.objects.filter(is_active=True).first()
        semester  = Semester.objects.filter(is_active=True).first()

        user = User.objects.create_user(
            username=username, password=reg_number,
            first_name=first_name, last_name=last_name,
            role="student", must_change_password=False
        )
        Student.objects.create(
            user=user, reg_number=reg_number, programme=programme,
            current_session=session, current_semester=semester, status=status
        )
        messages.success(request, f"Student {first_name} {last_name} added. Login: {username} / {reg_number}")
    return redirect("registrar_students")


# ─────────────────────────────────────────────────────────
# BATCH OPERATIONS
# ─────────────────────────────────────────────────────────

@login_required
def batch_operations(request):
    from fees.models import Payment
    context = {
        "total_students":   Student.objects.count(),
        "pending_payments": Payment.objects.filter(status="pending").count(),
    }
    return render(request, "registrar/batch_operations.html", context)


@login_required
def batch_generate_fees(request):
    import uuid
    from fees.models import Payment
    session    = Session.objects.filter(is_active=True).first()
    semester   = Semester.objects.filter(is_active=True).first()
    programmes = Programme.objects.all()
    programme_id = request.GET.get("programme")
    level        = request.GET.get("level")
    students = Student.objects.select_related("user","programme").all().order_by("reg_number")
    if programme_id:
        students = students.filter(programme_id=programme_id)
    if level:
        students = students.filter(reg_number__contains=f"/{level}/")
    student_data = []
    for s in students[:100]:
        has_any = Payment.objects.filter(student=s, session=session, status__in=["pending","approved"]).exists()
        student_data.append({"student": s, "has_any": has_any})
    if request.method == "POST":
        student_ids  = request.POST.getlist("student_ids")[:20]
        payment_type = request.POST.get("payment_type", "session")
        amount       = 50000 if payment_type == "session" else 25000
        generated = skipped = 0
        for sid in student_ids:
            try:
                student = Student.objects.get(pk=sid)
                if Payment.objects.filter(student=student, session=session, payment_type=payment_type, status__in=["pending","approved"]).exists():
                    skipped += 1
                    continue
                Payment.objects.create(
                    student=student, session=session, semester=semester,
                    payment_type=payment_type, amount=amount,
                    reference=f"CMT-{uuid.uuid4().hex[:8].upper()}", status="pending"
                )
                generated += 1
            except Student.DoesNotExist:
                pass
        messages.success(request, f"Generated {generated} invoice(s). Skipped {skipped} (already exist).")
        return redirect("batch_generate_fees")
    context = {"student_data": student_data, "session": session, "programmes": programmes,
               "selected_programme": programme_id, "selected_level": level}
    return render(request, "registrar/batch_generate_fees.html", context)


@login_required
def batch_approve_payments(request):
    from fees.models import Payment
    from django.utils import timezone
    programme_id = request.GET.get("programme")
    pay_type     = request.GET.get("pay_type")
    payments = Payment.objects.filter(status="pending").select_related(
        "student__user","student__programme","session").order_by("created_at")
    if programme_id:
        payments = payments.filter(student__programme_id=programme_id)
    if pay_type:
        payments = payments.filter(payment_type=pay_type)
    if request.method == "POST":
        payment_ids = request.POST.getlist("payment_ids")[:20]
        approved = 0
        for pid in payment_ids:
            try:
                p = Payment.objects.get(pk=pid, status="pending")
                p.status      = "approved"
                p.approved_by = request.user
                p.approved_at = timezone.now()
                p.receipt_no  = f"CMT-{p.pk:06d}"
                p.save()
                approved += 1
            except Payment.DoesNotExist:
                pass
        messages.success(request, f"Approved {approved} payment(s) successfully.")
        return redirect("batch_approve_payments")
    programmes = Programme.objects.all()
    context = {"payments": payments[:100], "programmes": programmes,
               "selected_programme": programme_id, "selected_pay_type": pay_type,
               "total_pending": Payment.objects.filter(status="pending").count()}
    return render(request, "registrar/batch_approve_payments.html", context)


@login_required
def batch_register_courses(request):
    from academics.models import CourseOutline, CourseRegistration
    semester   = Semester.objects.filter(is_active=True).first()
    programmes = Programme.objects.all()
    outlines   = CourseOutline.objects.filter(is_active=True).select_related("programme","semester")
    programme_id = request.GET.get("programme")
    level        = request.GET.get("level")
    outline_id   = request.GET.get("outline")
    students = Student.objects.select_related("user","programme").all().order_by("reg_number")
    if programme_id:
        students = students.filter(programme_id=programme_id)
    if level:
        students = students.filter(reg_number__contains=f"/{level}/")
    selected_outline = None
    if outline_id:
        try:
            selected_outline = CourseOutline.objects.get(pk=outline_id)
        except CourseOutline.DoesNotExist:
            pass
    student_data = []
    for s in students[:100]:
        count = CourseRegistration.objects.filter(student=s, semester=semester).count() if semester else 0
        student_data.append({"student": s, "registered_count": count, "already_registered": count > 0})
    if request.method == "POST":
        student_ids = request.POST.getlist("student_ids")[:20]
        outline_pk  = request.POST.get("outline_id")
        registered = skipped = 0
        try:
            outline = CourseOutline.objects.get(pk=outline_pk)
            courses = list(outline.courses.all())
        except CourseOutline.DoesNotExist:
            messages.error(request, "Invalid course outline.")
            return redirect("batch_register_courses")
        for sid in student_ids:
            try:
                student = Student.objects.get(pk=sid)
                CourseRegistration.objects.filter(student=student, semester=semester).delete()
                for course in courses:
                    CourseRegistration.objects.create(
                        student=student, semester=semester, course=course,
                        status="registered", is_carryover=False)
                registered += 1
            except Student.DoesNotExist:
                skipped += 1
        messages.success(request, f"Registered {len(courses)} course(s) for {registered} student(s).")
        return redirect("batch_register_courses")
    context = {"student_data": student_data, "outlines": outlines, "programmes": programmes,
               "semester": semester, "selected_programme": programme_id,
               "selected_level": level, "selected_outline": selected_outline, "outline_id": outline_id}
    return render(request, "registrar/batch_register_courses.html", context)


# ─────────────────────────────────────────────────────────
# SEMESTER RESULT SHEET
# ─────────────────────────────────────────────────────────

def get_grade(score):
    """Convert score to grade letter"""
    if score is None: return "-"
    if score >= 70: return "A"
    if score >= 60: return "B"
    if score >= 50: return "C"
    if score >= 45: return "D"
    if score >= 40: return "E"
    return "F"

def get_grade_point(score):
    """Convert score to grade point"""
    if score is None: return 0
    if score >= 70: return 5
    if score >= 60: return 4
    if score >= 50: return 3
    if score >= 45: return 2
    if score >= 40: return 1
    return 0


@login_required
def result_sheet_list(request):
    """List available result sheets by programme/level/semester"""
    from academics.models import CourseOutline, CourseRegistration
    outlines   = CourseOutline.objects.select_related("programme","semester__session").filter(is_active=True).order_by("programme__name","level","semester__name")
    programmes = Programme.objects.all()
    context    = {"outlines": outlines, "programmes": programmes}
    return render(request, "registrar/result_sheet_list.html", context)


@login_required
def result_entry(request, outline_id):
    """Enter/edit scores for students in a course outline"""
    from academics.models import CourseOutline, CourseRegistration
    outline  = get_object_or_404(CourseOutline, pk=outline_id)
    courses  = list(outline.courses.all().order_by("code"))
    semester = outline.semester

    # Get all students registered for this outline's semester with these courses
    student_ids = CourseRegistration.objects.filter(
        semester=semester,
        course__in=courses
    ).values_list("student_id", flat=True).distinct()

    level_year = "24" if "II" in outline.level else "25"
    students = Student.objects.filter(
        pk__in=student_ids,
        programme=outline.programme,
        reg_number__contains=f"/{level_year}/"
    ).select_related("user","programme").order_by("reg_number")

    if request.method == "POST":
        from academics.models import CourseRegistration
        saved = 0
        for student in students:
            for course in courses:
                key = f"score_{student.pk}_{course.pk}"
                score_str = request.POST.get(key, "").strip()
                if score_str:
                    try:
                        score = int(score_str)
                        score = max(0, min(100, score))
                        grade = get_grade(score)
                        reg, _ = CourseRegistration.objects.get_or_create(
                            student=student, semester=semester, course=course,
                            defaults={"status":"registered","is_carryover":False}
                        )
                        reg.score = score
                        reg.grade = grade
                        reg.status = "passed" if score >= 40 else "failed"
                        reg.save()
                        saved += 1
                    except ValueError:
                        pass
        messages.success(request, f"Saved {saved} score(s) successfully.")
        return redirect("result_entry", outline_id=outline_id)

    # Build result grid
    from academics.models import CourseRegistration
    result_grid = []
    for student in students:
        row = {"student": student, "scores": {}}
        for course in courses:
            reg = CourseRegistration.objects.filter(
                student=student, semester=semester, course=course
            ).first()
            row["scores"][course.pk] = {
                "score": reg.score if reg else None,
                "grade": reg.grade if reg else "-",
            }
        result_grid.append(row)

    context = {
        "outline":     outline,
        "courses":     courses,
        "result_grid": result_grid,
        "semester":    semester,
        "session":     semester.session if hasattr(semester, "session") else None,
    }
    return render(request, "registrar/result_entry.html", context)


@login_required
def result_sheet_pdf(request, outline_id):
    """Generate professional result sheet PDF using ReportLab"""
    import hashlib
    from io import BytesIO
    from django.http import HttpResponse
    from django.conf import settings
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import Table, TableStyle
    from academics.models import CourseOutline, CourseRegistration

    outline  = get_object_or_404(CourseOutline, pk=outline_id)
    courses  = list(outline.courses.all().order_by("code"))
    semester = outline.semester

    CMT_LOGO   = f"{settings.BASE_DIR}/static/images/cmt_logo.png.png"
    FUDMA_LOGO = f"{settings.BASE_DIR}/static/images/fudma_logo.png_optimized_250.png"

    GREEN  = colors.HexColor("#1a5c38")
    GOLD   = colors.HexColor("#c8881a")
    LGRAY  = colors.HexColor("#f5f5f5")
    WHITE  = colors.white
    BLACK  = colors.black

    # Get students
    student_ids = CourseRegistration.objects.filter(
        semester=semester, course__in=courses
    ).values_list("student_id", flat=True).distinct()

    level_year = "24" if "II" in outline.level else "25"
    students = Student.objects.filter(
        pk__in=student_ids,
        reg_number__contains=f"/{level_year}/"
    ).select_related("user","programme").order_by("reg_number")

    # Build data rows
    rows_data = []
    pass_count = carryover_count = 0

    for student in students:
        regs = {r.course_id: r for r in CourseRegistration.objects.filter(
            student=student, semester=semester, course__in=courses
        ).select_related("course")}

        tcr = tce = tgp = 0
        course_scores = []
        has_fail = False

        for course in courses:
            reg = regs.get(course.pk)
            score = reg.score if reg and reg.score is not None else None
            grade = get_grade(score)
            gp    = get_grade_point(score)
            units = course.unit
            tcr  += units
            tgp  += gp * units
            if score is not None and score >= 40:
                tce += units
            elif score is not None and score < 40:
                has_fail = True
            course_scores.append(f"{score if score is not None else '-'} {grade}")

        gpa = round(tgp/tcr, 2) if tcr > 0 else 0

        # Previous cumulative (other semesters)
        prev_regs = CourseRegistration.objects.filter(
            student=student, status__in=["passed","failed"]
        ).exclude(semester=semester).select_related("course")

        ccr = cce = cgp_prev = 0
        for pr in prev_regs:
            if pr.course and pr.score is not None:
                ccr += pr.course.unit
                cgp_prev += get_grade_point(pr.score) * pr.course.unit
                if pr.score >= 40:
                    cce += pr.course.unit
        prev_cgpa = round(cgp_prev/ccr, 2) if ccr > 0 else 0

        # Cumulative
        cum_ccr = tcr + ccr
        cum_cce = tce + cce
        cum_cgp = tgp + cgp_prev
        cum_cgpa = round(cum_cgp/cum_ccr, 2) if cum_ccr > 0 else 0

        remark = "PASS" if not has_fail else "C/O"
        if not has_fail: pass_count += 1
        else: carryover_count += 1

        rows_data.append({
            "student": student,
            "scores":  course_scores,
            "tcr": tcr, "tce": tce, "tgp": tgp, "gpa": f"{gpa:.2f}",
            "ccr": ccr, "cce": cce, "cgp": cgp_prev, "prev_cgpa": f"{prev_cgpa:.2f}",
            "cum_ccr": cum_ccr, "cum_cce": cum_cce, "cum_cgp": cum_cgp, "cum_cgpa": f"{cum_cgpa:.2f}",
            "remark": remark,
        })

    # ── PDF GENERATION ────────────────────────────────────
    buf = BytesIO()
    W, H = landscape(A4)
    c = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    def draw_page(c, page_num=1, total_pages=1):
        # Border
        c.setStrokeColor(GREEN)
        c.setLineWidth(2)
        c.rect(8*mm, 8*mm, W-16*mm, H-16*mm)
        c.setLineWidth(0.5)
        c.setStrokeColor(GOLD)
        c.rect(10*mm, 10*mm, W-20*mm, H-20*mm)

        # Header
        try:
            c.drawImage(CMT_LOGO,  13*mm, H-35*mm, width=22*mm, height=26*mm, preserveAspectRatio=True, mask="auto")
            c.drawImage(FUDMA_LOGO, W-35*mm, H-35*mm, width=22*mm, height=26*mm, preserveAspectRatio=True, mask="auto")
        except: pass

        c.setFillColor(GREEN)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(W/2, H-17*mm, "COLLEGE OF MANAGEMENT AND TECHNOLOGY KATSINA")
        c.setFillColor(BLACK)
        c.setFont("Helvetica", 8)
        c.drawCentredString(W/2, H-22*mm, "11, Batsari Road, Day Kofar Yandaka, Katsina")
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(W/2, H-26*mm, "Affiliated to")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(W/2, H-30*mm, "Federal University Dutsin-Ma Katsina")

        c.setLineWidth(1.5)
        c.setStrokeColor(GREEN)
        c.line(12*mm, H-33*mm, W-12*mm, H-33*mm)
        c.setLineWidth(0.5)
        c.setStrokeColor(GOLD)
        c.line(12*mm, H-34*mm, W-12*mm, H-34*mm)

        # Programme + title
        prog_name = outline.programme.name if outline.programme else ""
        sem_name  = str(semester) if semester else ""
        session   = semester.session if hasattr(semester, "session") and semester.session else ""

        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, H-38*mm, prog_name)
        c.setFont("Helvetica", 8)
        c.drawCentredString(W/2, H-42*mm, "Submission to the Academic Board, College of Professional and Continuing Studies")
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, H-46*mm, f"{outline.level.upper()}, {session} {sem_name.upper()} RESULT")

        if page_num > 1:
            c.setFont("Helvetica", 7)
            c.drawCentredString(W/2, H-49*mm, f"(continued — Page {page_num} of {total_pages})")

    def draw_table(c, rows_data, courses, y_start):
        # Column widths
        sn_w    = 7*mm
        stu_w   = 35*mm
        crs_w   = 14*mm  # per course
        cur_w   = 8*mm   # TCR,TCE,TGP,GPA
        prv_w   = 8*mm
        cum_w   = 8*mm
        rem_w   = 12*mm

        n_courses = len(courses)
        total_w = sn_w + stu_w + n_courses*crs_w + 4*cur_w + 4*prv_w + 4*cum_w + rem_w

        x0 = (W - total_w) / 2
        row_h = 9*mm
        hdr_h = 8*mm

        # Header row 1 - main groups
        sections = [
            (sn_w, "S/N", 2),
            (stu_w, "Student", 2),
            (n_courses*crs_w, "SEMESTER COURSES", 1),
            (4*cur_w, "CURRENT", 1),
            (4*prv_w, "PREVIOUS", 1),
            (4*cum_w, "CUMULATIVE", 1),
            (rem_w, "REMARK", 2),
        ]

        x = x0
        y = y_start
        c.setFillColor(GREEN)
        for w, label, rowspan in sections:
            c.rect(x, y - (hdr_h if rowspan == 2 else hdr_h/2+1), w, hdr_h if rowspan == 2 else hdr_h/2, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 6.5)
            ty = y - (hdr_h/2 if rowspan == 2 else hdr_h/4)
            c.drawCentredString(x + w/2, ty - 2, label)
            c.setFillColor(GREEN)
            x += w

        # Header row 2 - sub-columns
        y2 = y - hdr_h/2
        x  = x0 + sn_w + stu_w

        # Course codes + units
        for course in courses:
            c.setFillColor(GREEN)
            c.rect(x, y2 - hdr_h/2, crs_w, hdr_h/2, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(x + crs_w/2, y2 - hdr_h/4 + 1, course.code)
            c.setFont("Helvetica", 5)
            c.drawCentredString(x + crs_w/2, y2 - hdr_h/4 - 3, str(course.unit))
            x += crs_w

        # CURRENT sub-cols
        for label in ["TCR","TCE","TGP","GPA"]:
            c.setFillColor(GREEN)
            c.rect(x, y2 - hdr_h/2, cur_w, hdr_h/2, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(x + cur_w/2, y2 - hdr_h/4 - 1, label)
            x += cur_w

        # PREVIOUS sub-cols
        for label in ["CCR","CCE","CGP","CGPA"]:
            c.setFillColor(GREEN)
            c.rect(x, y2 - hdr_h/2, prv_w, hdr_h/2, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(x + prv_w/2, y2 - hdr_h/4 - 1, label)
            x += prv_w

        # CUMULATIVE sub-cols
        for label in ["CCR","CCE","CGP","CGPA"]:
            c.setFillColor(GREEN)
            c.rect(x, y2 - hdr_h/2, cum_w, hdr_h/2, fill=1, stroke=1)
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawCentredString(x + cum_w/2, y2 - hdr_h/4 - 1, label)
            x += cum_w

        # Data rows
        y_data = y - hdr_h
        for i, row in enumerate(rows_data):
            student = row["student"]
            bg = LGRAY if i % 2 == 0 else WHITE
            x = x0

            # Draw row background
            c.setFillColor(bg)
            c.rect(x, y_data - row_h, total_w, row_h, fill=1, stroke=0)

            # Row border
            c.setStrokeColor(colors.HexColor("#cccccc"))
            c.setLineWidth(0.3)
            c.line(x0, y_data - row_h, x0 + total_w, y_data - row_h)

            c.setFillColor(BLACK)

            # S/N
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + sn_w/2, y_data - row_h/2 - 2, str(i+1))
            x += sn_w

            # Student name + matric
            c.setFont("Helvetica-Bold", 6.5)
            name = student.user.get_full_name()
            if len(name) > 22: name = name[:22] + "."
            c.drawString(x + 1*mm, y_data - row_h/2 + 1, name)
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawString(x + 1*mm, y_data - row_h/2 - 4, student.reg_number)
            c.setFillColor(BLACK)
            x += stu_w

            # Course scores
            for score_grade in row["scores"]:
                c.setFont("Helvetica", 6.5)
                c.drawCentredString(x + crs_w/2, y_data - row_h/2 - 2, str(score_grade))
                x += crs_w

            # Current
            for val in [row["tcr"], row["tce"], row["tgp"], row["gpa"]]:
                c.setFont("Helvetica", 6.5)
                c.drawCentredString(x + cur_w/2, y_data - row_h/2 - 2, str(val))
                x += cur_w

            # Previous
            for val in [row["ccr"], row["cce"], row["cgp"], row["prev_cgpa"]]:
                c.setFont("Helvetica", 6.5)
                c.drawCentredString(x + prv_w/2, y_data - row_h/2 - 2, str(val))
                x += prv_w

            # Cumulative
            for val in [row["cum_ccr"], row["cum_cce"], row["cum_cgp"], row["cum_cgpa"]]:
                c.setFont("Helvetica", 6.5)
                c.drawCentredString(x + cum_w/2, y_data - row_h/2 - 2, str(val))
                x += cum_w

            # Remark
            c.setFillColor(GREEN if row["remark"] == "PASS" else colors.red)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x + rem_w/2, y_data - row_h/2 - 2, row["remark"])
            c.setFillColor(BLACK)

            y_data -= row_h

        # Outer table border
        c.setStrokeColor(GREEN)
        c.setLineWidth(0.8)
        c.rect(x0, y_data, total_w, y_start - y_data)

        # Vertical lines
        c.setLineWidth(0.4)
        c.setStrokeColor(colors.HexColor("#888888"))
        xv = x0
        for w in [sn_w, stu_w] + [crs_w]*n_courses + [cur_w]*4 + [prv_w]*4 + [cum_w]*4:
            xv += w
            c.line(xv, y_data, xv, y_start)

        return y_data

    def draw_footer(c, pass_count, carryover_count, total):
        y = 52*mm
        # Statistical report
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(BLACK)
        c.drawString(12*mm, y, "STATISTICAL REPORT")

        # Table
        data = [
            ["Total Registered", "Total Sat", "Passed", "Carryover"],
            [str(total), str(total), f"{pass_count} ({int(pass_count/total*100) if total else 0}%)", f"({carryover_count})"],
        ]
        tbl_x = 12*mm
        tbl_y = y - 2*mm
        col_ws = [50*mm, 50*mm, 50*mm, 50*mm]
        row_hs = [8*mm, 8*mm]

        for ri, row in enumerate(data):
            x = tbl_x
            for ci, cell in enumerate(row):
                bg = GREEN if ri == 0 else WHITE
                c.setFillColor(bg)
                c.setStrokeColor(BLACK)
                c.setLineWidth(0.5)
                c.rect(x, tbl_y - (ri+1)*row_hs[ri], col_ws[ci], row_hs[ri], fill=1, stroke=1)
                c.setFillColor(WHITE if ri == 0 else BLACK)
                c.setFont("Helvetica-Bold" if ri == 0 else "Helvetica", 7)
                lines = cell.split("\n")
                for li, line in enumerate(lines):
                    c.drawCentredString(x + col_ws[ci]/2, tbl_y - (ri+1)*row_hs[ri] + row_hs[ri]/2 + (3 if len(lines)>1 else 0) - li*7, line)
                x += col_ws[ci]

        # Signature lines
        y_sig = 35*mm
        sigs = [
            ("Dr. Shehu Sani", "Provost - CMT"),
            ("________________________", "Head of Department"),
            ("Dr Jamilu Ajiya", "Provost - CPCS, FUDMA"),
        ]
        sig_x = [12*mm, W/2 - 30*mm, W - 80*mm]
        for i, (name, title) in enumerate(sigs):
            c.setFont("Helvetica", 8)
            c.setFillColor(BLACK)
            c.line(sig_x[i], y_sig + 6*mm, sig_x[i] + 60*mm, y_sig + 6*mm)
            c.drawString(sig_x[i], y_sig + 2*mm, name)
            c.drawString(sig_x[i], y_sig - 3*mm, title)

        # Grade key
        y_key = 20*mm
        c.setFont("Helvetica-Bold", 7)
        c.drawString(12*mm, y_key, "GRADING: ")
        c.setFont("Helvetica", 7)
        key = "A=70-100(5pts)  B=60-69(4pts)  C=50-59(3pts)  D=45-49(2pts)  E=40-44(1pt)  F=<40(0pts)"
        c.drawString(35*mm, y_key, key)

        # CGPA classification
        c.setFont("Helvetica-Bold", 7)
        c.drawString(12*mm, y_key - 5*mm, "CLASS: ")
        c.setFont("Helvetica", 7)
        cls = "4.50-5.00=DISTINCTION  3.50-4.49=UPPER CREDIT  2.50-3.49=LOWER CREDIT  1.00-2.49=PASS"
        c.drawString(35*mm, y_key - 5*mm, cls)

    # Draw pages
    y_content_start = H - 52*mm
    y_footer_end    = 58*mm
    available_h     = y_content_start - y_footer_end

    draw_page(c, 1, 1)
    y_after = draw_table(c, rows_data, courses, y_content_start)
    draw_footer(c, pass_count, carryover_count, len(rows_data))

    c.save()
    buf.seek(0)

    prog_name = outline.programme.name.replace(" ","_").upper() if outline.programme else "PROG"
    fname = f"Result_{prog_name}_{outline.level.replace(' ','_')}_{semester}.pdf"
    response = HttpResponse(buf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'filename="{fname}"'
    return response


@login_required
def bulk_upload_results(request, outline_id):
    """Bulk upload semester results via CSV"""
    import csv, io
    from academics.models import CourseOutline, CourseRegistration

    outline  = get_object_or_404(CourseOutline, pk=outline_id)
    courses  = list(outline.courses.all().order_by("code"))
    semester = outline.semester

    results  = []
    errors   = []
    preview  = []

    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Please select a CSV file.")
            return redirect("bulk_upload_results", outline_id=outline_id)

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "File must be a .csv file.")
            return redirect("bulk_upload_results", outline_id=outline_id)

        try:
            decoded = csv_file.read().decode("utf-8-sig")
            reader  = csv.DictReader(io.StringIO(decoded))
            headers = reader.fieldnames or []

            saved = skipped = failed = 0

            for row_num, row in enumerate(reader, start=2):
                matric = row.get("MATRIC_NO", row.get("matric_no", row.get("Matric No", ""))).strip()
                if not matric:
                    errors.append(f"Row {row_num}: Missing matric number")
                    continue

                try:
                    student = Student.objects.get(reg_number=matric)
                except Student.DoesNotExist:
                    errors.append(f"Row {row_num}: Student '{matric}' not found")
                    skipped += 1
                    continue

                row_result = {"matric": matric, "name": student.user.get_full_name(), "scores": [], "status": "OK"}

                for course in courses:
                    # Try course code as column header
                    score_str = row.get(course.code, row.get(course.code.lower(), "")).strip()
                    if not score_str:
                        row_result["scores"].append({"code": course.code, "score": "-", "grade": "-"})
                        continue

                    try:
                        score = int(float(score_str))
                        score = max(0, min(100, score))
                        grade = get_grade(score)

                        reg, created = CourseRegistration.objects.get_or_create(
                            student=student,
                            semester=semester,
                            course=course,
                            defaults={"status": "registered", "is_carryover": False}
                        )
                        reg.score  = score
                        reg.grade  = grade
                        reg.status = "passed" if score >= 40 else "failed"
                        reg.save()
                        saved += 1
                        row_result["scores"].append({"code": course.code, "score": score, "grade": grade})
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_num}, {course.code}: Invalid score '{score_str}'")
                        row_result["scores"].append({"code": course.code, "score": "ERR", "grade": "-"})

                results.append(row_result)

            if errors:
                for e in errors[:5]:
                    messages.warning(request, e)
            messages.success(request, f"Upload complete: {saved} scores saved, {skipped} students not found.")

        except Exception as e:
            messages.error(request, f"Error reading CSV: {str(e)}")

    # Generate sample CSV for download
    sample_rows = []
    header_row  = ["MATRIC_NO"] + [c.code for c in courses]
    sample_rows.append(header_row)

    # Add sample student rows
    from academics.models import CourseRegistration as CR
    student_ids = CR.objects.filter(semester=semester, course__in=courses).values_list("student_id", flat=True).distinct()
    level_year  = "24" if "II" in outline.level else "25"
    students    = Student.objects.filter(
        pk__in=student_ids,
        programme=outline.programme,
        reg_number__contains=f"/{level_year}/"
    ).order_by("reg_number")[:5]

    for s in students:
        row = [s.reg_number] + ["" for _ in courses]
        sample_rows.append(row)

    context = {
        "outline":     outline,
        "courses":     courses,
        "semester":    semester,
        "results":     results,
        "errors":      errors,
        "sample_rows": sample_rows,
        "header_row":  header_row,
    }
    return render(request, "registrar/bulk_upload_results.html", context)


@login_required
def download_result_template(request, outline_id):
    """Download blank CSV template for result upload"""
    import csv
    from django.http import HttpResponse
    from academics.models import CourseOutline, CourseRegistration as CR

    outline  = get_object_or_404(CourseOutline, pk=outline_id)
    courses  = list(outline.courses.all().order_by("code"))
    semester = outline.semester

    response = HttpResponse(content_type="text/csv")
    fname    = f"Result_Template_{outline.programme.name.replace(' ','_')}_{outline.level.replace(' ','_')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'

    writer = csv.writer(response)
    # Header
    writer.writerow(["MATRIC_NO"] + [c.code for c in courses])

    # Get registered students
    student_ids = CR.objects.filter(
        semester=semester, course__in=courses
    ).values_list("student_id", flat=True).distinct()
    level_year  = "24" if "II" in outline.level else "25"
    students    = Student.objects.filter(
        pk__in=student_ids,
        programme=outline.programme,
        reg_number__contains=f"/{level_year}/"
    ).order_by("reg_number")

    for student in students:
        regs = {r.course_id: r.score for r in CR.objects.filter(student=student, semester=semester, course__in=courses)}
        row  = [student.reg_number] + [regs.get(c.pk, "") or "" for c in courses]
        writer.writerow(row)

    return response
