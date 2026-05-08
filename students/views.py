from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from accounts.models import User
from academics.models import Programme, Course
from core.models import Session, Semester
from fees.models import FeePayment
from .models import Student, CourseRegistration


def role_required(*roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "Access denied.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@role_required("admin", "academic_officer")
def admin_dashboard(request):
    context = {
        "total_students": Student.objects.filter(status="active").count(),
        "total_programmes": Programme.objects.count(),
        "pending_payments": FeePayment.objects.filter(status="pending").count(),
        "active_session": Session.objects.filter(is_active=True).first(),
        "active_semester": Semester.objects.filter(is_active=True).first(),
        "recent_students": Student.objects.order_by("-date_enrolled")[:5],
    }
    return render(request, "students/admin_dashboard.html", context)


@role_required("admin", "academic_officer")
def student_list(request):
    students = Student.objects.select_related("user", "programme", "current_session").all()
    programmes = Programme.objects.all()
    if request.GET.get("programme"):
        students = students.filter(programme__id=request.GET["programme"])
    if request.GET.get("status"):
        students = students.filter(status=request.GET["status"])
    return render(request, "students/student_list.html", {"students": students, "programmes": programmes})


@role_required("admin")
def add_student(request):
    if request.method == "POST":
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        email = request.POST.get("email", "")
        reg_number = request.POST["reg_number"]
        programme_id = request.POST["programme"]
        session_id = request.POST["session"]
        semester_id = request.POST["semester"]
        if User.objects.filter(username=reg_number).exists():
            messages.error(request, "Registration number already exists.")
            return redirect("add_student")
        user = User.objects.create_user(
            username=reg_number, password=reg_number,
            first_name=first_name, last_name=last_name,
            email=email, role="student", must_change_password=True,
        )
        Student.objects.create(
            user=user, reg_number=reg_number,
            programme=Programme.objects.get(pk=programme_id),
            current_session=Session.objects.get(pk=session_id),
            current_semester=Semester.objects.get(pk=semester_id),
        )
        messages.success(request, f"Student {first_name} {last_name} added.")
        return redirect("student_list")
    return render(request, "students/add_student.html", {
        "programmes": Programme.objects.all(),
        "sessions": Session.objects.all(),
        "semesters": Semester.objects.all(),
    })


@role_required("admin", "academic_officer")
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    registrations = CourseRegistration.objects.filter(student=student).prefetch_related("courses")
    payments = FeePayment.objects.filter(student=student)
    return render(request, "students/student_detail.html", {
        "student": student, "registrations": registrations, "payments": payments,
    })


@role_required("admin")
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.user.delete()
    messages.success(request, "Student deleted.")
    return redirect("student_list")


@role_required("admin")
def migrate_students(request):
    if request.method == "POST":
        active_session = Session.objects.filter(is_active=True).first()
        if not active_session:
            messages.error(request, "No active session found.")
            return redirect("admin_dashboard")
        count = Student.objects.filter(status="active").update(current_session=active_session)
        messages.success(request, f"{count} students migrated to {active_session}.")
    return redirect("admin_dashboard")


@role_required("admin", "academic_officer")
def admin_photo_capture(request):
    student = None
    if request.method == "POST":
        reg_number = request.POST.get("reg_number", "").strip()
        webcam_data = request.POST.get("webcam_data", "")
        file_upload = request.FILES.get("photo_file")
        try:
            student = Student.objects.get(reg_number=reg_number)
            if webcam_data:
                fmt, imgstr = webcam_data.split(";base64,")
                ext = fmt.split("/")[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                student.photo = data
                student.save()
                messages.success(request, f"Photo saved for {student.user.get_full_name()}.")
            elif file_upload:
                student.photo = file_upload
                student.save()
                messages.success(request, f"Photo uploaded for {student.user.get_full_name()}.")
        except Student.DoesNotExist:
            messages.error(request, f"No student found: {reg_number}")
    lookup = request.GET.get("reg", "").strip()
    if lookup and not student:
        try:
            student = Student.objects.get(reg_number=lookup)
        except Student.DoesNotExist:
            messages.error(request, f"No student found: {lookup}")
    return render(request, "students/admin_photo_capture.html", {"student": student})


@role_required("admin")
def user_management(request):
    if request.method == "POST":
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        username = request.POST["username"]
        email = request.POST.get("email", "")
        role = request.POST["role"]
        password = request.POST.get("password", "") or username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name,
                email=email, role=role,
            )
            messages.success(request, f"User {first_name} {last_name} created as {role}.")
    users = User.objects.all().order_by("role", "first_name")
    return render(request, "students/user_management.html", {"users": users})


@role_required("admin", "academic_officer", "registrar")
def semester_result(request):
    programmes = Programme.objects.all()
    semesters = Semester.objects.all()
    result_data = None
    selected = {}
    if request.GET.get("programme") and request.GET.get("semester"):
        prog_id = request.GET["programme"]
        sem_id = request.GET["semester"]
        programme = Programme.objects.get(pk=prog_id)
        semester = Semester.objects.get(pk=sem_id)
        sem_num = 1 if semester.name == "first" else 2
        if programme.level == "diploma2":
            sem_num += 2
        registrations = CourseRegistration.objects.filter(
            semester=semester, student__programme=programme, student__status="active"
        ).select_related("student__user").prefetch_related("courses")
        courses = Course.objects.filter(programme=programme, semester_number=sem_num).order_by("code")
        result_data = {
            "programme": programme, "semester": semester, "courses": courses,
            "rows": [{"student": r.student, "reg": r} for r in registrations],
        }
        selected = {"programme": prog_id, "semester": sem_id}
    return render(request, "students/semester_result.html", {
        "programmes": programmes, "semesters": semesters,
        "result_data": result_data, "selected": selected,
    })


@role_required("admin", "academic_officer")
def bulk_import(request):
    results = None
    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]
        decoded = csv_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        active_session = Session.objects.filter(is_active=True).first()
        active_semester = Semester.objects.filter(is_active=True).first()
        rows = []
        total = created = skipped = errors = 0
        for row in reader:
            total += 1
            name = row.get("name", "").strip()
            reg = row.get("reg_number", "").strip()
            prog_code = row.get("programme_code", "").strip()
            level = row.get("level", "").strip()
            try:
                programme = Programme.objects.get(code__iexact=prog_code, level=level)
                if User.objects.filter(username=reg).exists():
                    rows.append({"name": name, "reg_number": reg, "programme": prog_code, "status": "Skipped", "status_class": "skip", "note": "Already exists"})
                    skipped += 1
                    continue
                parts = name.split(" ", 1)
                user = User.objects.create_user(
                    username=reg, password=reg,
                    first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
                    role="student", must_change_password=True,
                )
                Student.objects.create(user=user, reg_number=reg, programme=programme,
                    current_session=active_session, current_semester=active_semester)
                rows.append({"name": name, "reg_number": reg, "programme": str(programme), "status": "Created", "status_class": "ok", "note": "OK"})
                created += 1
            except Programme.DoesNotExist:
                rows.append({"name": name, "reg_number": reg, "programme": prog_code, "status": "Error", "status_class": "err", "note": "Programme not found"})
                errors += 1
            except Exception as e:
                rows.append({"name": name, "reg_number": reg, "programme": prog_code, "status": "Error", "status_class": "err", "note": str(e)})
                errors += 1
        results = {"total": total, "created": created, "skipped": skipped, "errors": errors, "rows": rows}
    return render(request, "students/bulk_import.html", {"results": results})


@role_required("admin", "academic_officer")
def download_csv_template(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=student_import_template.csv"
    writer = csv.writer(response)
    writer.writerow(["name", "reg_number", "programme_code", "level"])
    writer.writerow(["Yusuf Abdullahi", "DPL/BUS/24/047", "BUS", "diploma2"])
    return response


@role_required("admin", "academic_officer")
def export_students_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=students_export.csv"
    writer = csv.writer(response)
    writer.writerow(["name", "reg_number", "programme", "level", "session", "status"])
    for s in Student.objects.select_related("user", "programme", "current_session").all():
        writer.writerow([s.user.get_full_name(), s.reg_number, str(s.programme), s.programme.level, str(s.current_session), s.status])
    return response


@role_required("admin", "registrar")
def registrar_dashboard(request):
    students = Student.objects.all()
    context = {
        "total_students": students.count(),
        "pending_payments": FeePayment.objects.filter(status="pending").count(),
        "approved_payments": FeePayment.objects.filter(status="approved").count(),
        "no_photo": students.filter(photo="").count(),
        "recent_students": students.select_related("user", "programme").order_by("-date_enrolled")[:8],
    }
    return render(request, "students/registrar_dashboard.html", context)


@role_required("admin", "registrar")
def registrar_students(request):
    students = Student.objects.select_related("user", "programme", "current_session").all()
    q = request.GET.get("q", "")
    prog = request.GET.get("programme", "")
    if q:
        students = students.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(reg_number__icontains=q))
    if prog:
        students = students.filter(programme__id=prog)
    return render(request, "students/registrar_students.html", {
        "students": students, "programmes": Programme.objects.all(), "q": q,
    })


@role_required("admin", "registrar")
def registrar_fees(request):
    action = request.POST.get("action", "")
    if request.method == "POST":
        if action == "generate":
            try:
                student = Student.objects.get(pk=request.POST["student_id"])
                ptype = request.POST["payment_type"]
                amount = 50000 if ptype == "session" else 25000
                if FeePayment.objects.filter(student=student, session=student.current_session, payment_type=ptype, status__in=["pending", "approved"]).exists():
                    messages.warning(request, f"{student.user.get_full_name()} already has a {ptype} payment.")
                else:
                    FeePayment.objects.create(
                        student=student, session=student.current_session,
                        payment_type=ptype, amount=amount,
                        receipt_number=f"RCP-{uuid.uuid4().hex[:8].upper()}",
                        status="pending",
                    )
                    messages.success(request, f"Payment of N{amount:,} generated.")
            except Student.DoesNotExist:
                messages.error(request, "Student not found.")
        elif action == "approve":
            try:
                p = FeePayment.objects.get(pk=request.POST["payment_id"])
                p.status = "approved"
                p.approved_by = request.user
                p.date_approved = timezone.now()
                p.save()
                messages.success(request, f"Payment {p.receipt_number} approved.")
            except FeePayment.DoesNotExist:
                messages.error(request, "Payment not found.")
        elif action == "reject":
            try:
                p = FeePayment.objects.get(pk=request.POST["payment_id"])
                p.status = "rejected"
                p.save()
                messages.warning(request, f"Payment {p.receipt_number} rejected.")
            except FeePayment.DoesNotExist:
                messages.error(request, "Payment not found.")
    pending = FeePayment.objects.filter(status="pending").select_related("student__user", "session").order_by("-date_requested")
    approved = FeePayment.objects.filter(status="approved").select_related("student__user", "session").order_by("-date_approved")[:30]
    students = Student.objects.select_related("user").all()
    return render(request, "students/registrar_fees.html", {"pending": pending, "approved": approved, "students": students})


@role_required("admin", "registrar")
def registrar_documents(request):
    students = Student.objects.select_related("user", "programme", "current_session").all()
    q = request.GET.get("q", "")
    if q:
        students = students.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(reg_number__icontains=q))
    return render(request, "students/registrar_documents.html", {"students": students, "q": q})


@role_required("admin", "registrar")
def registrar_photo(request):
    student = None
    if request.method == "POST":
        reg_number = request.POST.get("reg_number", "").strip()
        webcam_data = request.POST.get("webcam_data", "")
        file_upload = request.FILES.get("photo_file")
        try:
            student = Student.objects.get(reg_number=reg_number)
            if webcam_data:
                fmt, imgstr = webcam_data.split(";base64,")
                ext = fmt.split("/")[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                student.photo = data
                student.save()
                messages.success(request, f"Photo saved for {student.user.get_full_name()}.")
            elif file_upload:
                student.photo = file_upload
                student.save()
                messages.success(request, f"Photo uploaded for {student.user.get_full_name()}.")
            else:
                messages.error(request, "No photo provided.")
        except Student.DoesNotExist:
            messages.error(request, f"No student found: {reg_number}")
    lookup = request.GET.get("reg", "").strip()
    if lookup and not student:
        try:
            student = Student.objects.get(reg_number=lookup)
        except Student.DoesNotExist:
            messages.error(request, f"No student found: {lookup}")
    return render(request, "students/registrar_photo.html", {"student": student})


@role_required("student")
def student_dashboard(request):
    from academics.models import CourseRegistration as AcadCR
    student  = get_object_or_404(Student, user=request.user)
    session  = Session.objects.filter(is_active=True).first()
    semester = Semester.objects.filter(is_active=True).first()

    registrations = AcadCR.objects.filter(
        student=student, semester=semester
    ).select_related("course", "semester") if semester else []

    total_units = sum(r.course.unit for r in registrations)
    reg_count   = len(list(registrations))

    from fees.models import Payment as FeePayment2
    payments = FeePayment2.objects.filter(student=student).order_by("-created_at")[:5]

    has_paid = FeePayment2.objects.filter(
        student=student, status="approved"
    ).exists()

    return render(request, "students/student_dashboard.html", {
        "student": student,
        "session": session,
        "semester": semester,
        "registrations": registrations,
        "total_units": total_units,
        "reg_count": reg_count,
        "payments": payments,
        "has_paid": has_paid,
    })


@role_required("student")
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)
    return render(request, "students/profile.html", {"student": student})


@role_required("student")
def upload_photo(request):
    student = get_object_or_404(Student, user=request.user)
    if request.method == "POST":
        webcam_data = request.POST.get("webcam_data", "")
        file_upload = request.FILES.get("photo_file")
        if webcam_data:
            fmt, imgstr = webcam_data.split(";base64,")
            ext = fmt.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
            student.photo = data
            student.save()
            messages.success(request, "Photo saved from webcam.")
        elif file_upload:
            student.photo = file_upload
            student.save()
            messages.success(request, "Photo uploaded successfully.")
        else:
            messages.error(request, "No photo provided.")
        return redirect("student_profile")
    return render(request, "students/upload_photo.html", {"student": student})


@role_required("student")
def register_courses(request):
    from fees.models import Payment as FP2
    from academics.models import CourseRegistration, Course

    student         = get_object_or_404(Student, user=request.user)
    active_semester = Semester.objects.filter(is_active=True).first()

    if not active_semester:
        messages.error(request, "No active semester. Contact admin.")
        return redirect("student_dashboard")

    # Payment check
    paid = FP2.objects.filter(student=student, status="approved").exists()
    if not paid:
        messages.error(request, "Please pay your fees before registering courses.")
        return redirect("student_dashboard")

    existing_reg = CourseRegistration.objects.filter(
        student=student, semester=active_semester
    ).first()

    from academics.models import CourseOutline
    try:
        outline = CourseOutline.objects.get(
            programme=student.programme,
            level=student.level,
            semester=active_semester,
            is_active=True
        )
        available_courses = outline.courses.all()
    except CourseOutline.DoesNotExist:
        available_courses = []

    if request.method == "POST":
        selected_ids = request.POST.getlist("courses")
        reg = existing_reg or CourseRegistration.objects.create(
            student=student, semester=active_semester
        )
        reg.courses.set(selected_ids)
        reg.save()
        messages.success(request, "Courses registered successfully.")
        return redirect("my_courses")

    return render(request, "students/register_courses.html", {
        "student": student,
        "courses": available_courses,
        "existing_reg": existing_reg,
        "active_semester": active_semester,
    })


@role_required("student")
def my_courses(request):
    student = get_object_or_404(Student, user=request.user)
    active_semester = Semester.objects.filter(is_active=True).first()
    registration = CourseRegistration.objects.filter(student=student, semester=active_semester).prefetch_related("courses").first()
    return render(request, "students/my_courses.html", {
        "student": student, "registration": registration, "active_semester": active_semester,
    })


@login_required
def print_course_reg(request):
    from academics.models import CourseRegistration
    student = get_object_or_404(Student, user=request.user)
    semester = Semester.objects.filter(is_active=True).first()
    registrations = CourseRegistration.objects.filter(student=student, semester=semester).select_related("course", "semester") if semester else []
    total_units = sum(r.course.unit for r in registrations)
    return render(request, "students/print_course_reg.html", {"student": student, "semester": semester, "registrations": registrations, "total_units": total_units})


@login_required
def generate_payment(request):
    import uuid
    from fees.models import Payment
    student  = get_object_or_404(Student, user=request.user)
    session  = Session.objects.filter(is_active=True).first()
    semester = Semester.objects.filter(is_active=True).first()
    if request.method == "POST":
        pay_type = request.POST.get("payment_type")
        amount   = 25000 if pay_type == "semester" else 50000
        ref      = f"CMT-{uuid.uuid4().hex[:10].upper()}"
        existing = Payment.objects.filter(student=student, session=session, payment_type=pay_type, status__in=["pending","approved"]).first()
        if existing:
            messages.warning(request, f"You already have a {pay_type} payment. Ref: {existing.reference}")
            return redirect("my_payments")
        Payment.objects.create(student=student, session=session, semester=semester, payment_type=pay_type, amount=amount, reference=ref, status="pending")
        messages.success(request, f"Invoice of \u20a6{amount:,} generated. Ref: {ref}. Pay at the bank then upload evidence.")
        return redirect("my_payments")
    from fees.models import Payment
    existing_payments = Payment.objects.filter(student=student, session=session)
    has_semester = existing_payments.filter(payment_type="semester").exists()
    has_session  = existing_payments.filter(payment_type="session").exists()
    return render(request, "students/generate_payment.html", {"student": student, "session": session, "has_semester": has_semester, "has_session": has_session, "existing_payments": existing_payments})


@login_required
def my_payments(request):
    from fees.models import Payment
    student  = get_object_or_404(Student, user=request.user)
    payments = Payment.objects.filter(student=student).order_by("-date_requested")
    return render(request, "students/my_payments.html", {"student": student, "payments": payments})


@login_required
def student_receipt(request, payment_id):
    from fees.models import Payment
    from students.pdf_utils import render_to_pdf
    payment  = get_object_or_404(Payment, pk=payment_id, student__user=request.user, status="approved")
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()
    ctx = {"payment": payment, "semester": semester, "session": session}
    response = render_to_pdf("documents/receipt_pdf.html", ctx)
    fname = f"Receipt_{payment.receipt_no}_{payment.student.reg_number.replace('/', '_')}.pdf"
    response["Content-Disposition"] = f'filename="{fname}"'
    return response


@login_required
def exam_card(request, student_id=None):
    from academics.models import CourseRegistration
    if student_id:
        student = get_object_or_404(Student, pk=student_id)
    else:
        student = get_object_or_404(Student, user=request.user)
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()
    registrations = CourseRegistration.objects.filter(student=student, semester=semester).select_related("course", "semester") if semester else []
    ref = ("EC" + str(abs(hash(student.reg_number))))[:10].upper()
    return render(request, "documents/exam_card.html", {"student": student, "semester": semester, "session": session, "registrations": registrations, "exam_card_ref": ref})


@login_required
def course_reg_form(request, student_id):
    from academics.models import CourseRegistration
    student  = get_object_or_404(Student, pk=student_id)
    semester = Semester.objects.filter(is_active=True).first()
    registrations = CourseRegistration.objects.filter(student=student, semester=semester).select_related("course", "semester") if semester else []
    total_units = sum(r.course.unit for r in registrations)
    return render(request, "students/print_course_reg.html", {"student": student, "semester": semester, "registrations": registrations, "total_units": total_units})


@login_required
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)
    return render(request, "students/profile.html", {"student": student})
