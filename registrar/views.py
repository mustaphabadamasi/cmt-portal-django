from django.shortcuts import render, redirect, get_object_or_404
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
    return render(request, "registrar/students.html", {"students": all_students})


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
    payment = get_object_or_404(Payment, pk=payment_id, status="approved")
    return render(request, "registrar/receipt.html", {"payment": payment})


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
