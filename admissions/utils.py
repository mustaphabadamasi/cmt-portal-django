def generate_matric(programme, session_year):
    from students.models import Student
    yr = str(session_year)[-2:]
    prefix = f"DPL/{programme.code}/{yr}"
    max_num = 0
    for s in Student.objects.filter(reg_number__startswith=prefix + "/"):
        try:
            num = int(s.reg_number.split("/")[-1])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            pass
    return f"{prefix}/{max_num + 1:03d}"

def admit_applicant(application, admitted_by):
    from django.utils import timezone
    from accounts.models import User
    from students.models import Student
    from core.models import Session, Semester
    app_num = application.application_number
    # Get or create user (handles retry after partial failure)
    user, created = User.objects.get_or_create(
        username=app_num,
        defaults={
            "first_name": application.first_name,
            "last_name":  application.last_name,
            "email":      application.email,
            "role":       "student",
            "must_change_password": False,
        }
    )
    if created:
        user.set_password(app_num)
        user.save()
    student, _ = Student.objects.get_or_create(user=user, defaults=dict(
        user=user,
        reg_number=app_num,
        programme=application.programme,
        current_session=Session.objects.filter(is_active=True).first(),
        current_semester=Semester.objects.filter(is_active=True).first(),
        status="active",
        date_of_birth=application.date_of_birth,
        gender=application.gender,
    ))
    if application.photo:
        try:
            import shutil, os
            from django.conf import settings as djs
            dest_dir = os.path.join(djs.MEDIA_ROOT, "students", "admitted")
            os.makedirs(dest_dir, exist_ok=True)
            ext = os.path.splitext(application.photo.name)[1]
            dest = os.path.join(dest_dir, app_num.replace("/","_") + ext)
            shutil.copy(application.photo.path, dest)
            student.photo = os.path.relpath(dest, djs.MEDIA_ROOT)
            student.save()
        except Exception:
            pass
    application.status = "admitted"
    application.admitted_by = admitted_by
    application.admission_date = timezone.now()
    application.student = student
    application.save()
    try:
        from notifications.utils import notify
        notify(recipient=user, ntype="general",
               title="You have been admitted to CMT Katsina!",
               message=f"Login with {app_num}. Next: generate school fee invoice.",
               link="/students/dashboard/")
    except Exception:
        pass
    return student

def assign_matric(invoice, approved_by):
    from django.utils import timezone
    application = invoice.application
    student = application.student
    if not student:
        raise ValueError("No student linked to this application")
    session_year = int(str(application.session.name).split("/")[0])
    matric = generate_matric(application.programme, session_year)
    student.reg_number = matric
    student.save()
    user = student.user
    user.username = matric
    user.set_password(matric)
    user.save()
    application.matric_number = matric
    application.status = "school_fee_approved"
    application.save()
    invoice.status = "approved"
    invoice.approved_by = approved_by
    invoice.approved_at = timezone.now()
    invoice.save()
    try:
        from notifications.utils import notify
        notify(recipient=user, ntype="result",
               title=f"Matric Number Assigned: {matric}",
               message=f"New login: {matric} / {matric}. Proceed to course registration.",
               link="/students/dashboard/")
    except Exception:
        pass
    return matric