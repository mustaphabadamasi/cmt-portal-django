from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import CourseResult, ResultBatch, compute_grade
from academics.models import Course
from core.models import Semester, Session
from students.models import Student, CourseRegistration


# ── LECTURER VIEWS ────────────────────────────────────────────────────────────

@login_required
def lecturer_result_courses(request):
    """Lecturer sees their courses for result entry."""
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()
    # Get courses this lecturer teaches
    from lecturers.models import LecturerCourse
    try:
        lc_courses = LecturerCourse.objects.filter(
            lecturer__user=request.user
        ).select_related('course')
        courses = [lc.course for lc in lc_courses]
    except Exception:
        courses = []

    # Get batch status and student counts for each course
    batch_status   = {}
    student_counts = {}
    for c in courses:
        try:
            b = ResultBatch.objects.get(lecturer=request.user, course=c, semester=semester)
            batch_status[c.id] = b
        except ResultBatch.DoesNotExist:
            batch_status[c.id] = None
        # Count registered students
        try:
            count = CourseRegistration.objects.filter(
                courses=c, semester=semester, is_approved=True
            ).count()
            student_counts[c.id] = count
        except Exception:
            student_counts[c.id] = 0

    return render(request, 'results/lecturer/courses.html', {
        'courses': courses, 'semester': semester,
        'session': session, 'batch_status': batch_status,
        'student_counts': student_counts,
    })


@login_required
def enter_results(request, course_id):
    """Lecturer enters CA + Exam scores for all students in a course."""
    course   = get_object_or_404(Course, pk=course_id)
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()

    # Get or create batch
    batch, _ = ResultBatch.objects.get_or_create(
        lecturer=request.user, course=course, semester=semester,
        defaults={'session': session}
    )

    if batch.status == 'approved':
        # Allow viewing and downloading — just block editing
        results  = CourseResult.objects.filter(
            course=course, semester=semester
        ).select_related('student','student__user').order_by('student__reg_number')
        existing = {r.student_id: r for r in results}
        return render(request, 'results/lecturer/enter_results.html', {
            'course': course, 'semester': semester, 'session': session,
            'students': [r.student for r in results],
            'existing': existing, 'batch': batch,
        })

    # Get registered students
    # Get students registered for this course this semester
    registrations = CourseRegistration.objects.filter(
        courses=course, semester=semester
    ).select_related('student', 'student__user').order_by('student__reg_number')

    students = [r.student for r in registrations]

    # Get existing results
    existing = {
        r.student_id: r for r in CourseResult.objects.filter(
            course=course, semester=semester
        )
    }

    if request.method == 'POST':
        action = request.POST.get('action','save')
        errors = []
        with transaction.atomic():
            for student in students:
                ca_str   = request.POST.get(f'ca_{student.id}','').strip()
                exam_str = request.POST.get(f'exam_{student.id}','').strip()
                if not ca_str and not exam_str:
                    continue
                try:
                    ca   = float(ca_str)   if ca_str   else None
                    exam = float(exam_str) if exam_str else None
                    if ca is not None and (ca < 0 or ca > 40):
                        errors.append(f"{student.reg_number}: CA must be 0-40")
                        continue
                    if exam is not None and (exam < 0 or exam > 60):
                        errors.append(f"{student.reg_number}: Exam must be 0-60")
                        continue
                    CourseResult.objects.update_or_create(
                        student=student, course=course, semester=semester,
                        defaults={
                            'session': session,
                            'ca_score': ca,
                            'exam_score': exam,
                            'entered_by': request.user,
                            'status': 'draft',
                        }
                    )
                except ValueError:
                    errors.append(f"{student.reg_number}: Invalid score")

        if errors:
            for e in errors: messages.error(request, e)
        else:
            if action == 'submit':
                # Check all students have scores
                entered = CourseResult.objects.filter(
                    course=course, semester=semester,
                    total_score__isnull=False
                ).count()
                if entered < len(students):
                    messages.error(request,
                        f'Please enter scores for all {len(students)} students before submitting. '
                        f'({entered} entered so far)')
                else:
                    CourseResult.objects.filter(
                        course=course, semester=semester
                    ).update(status='submitted')
                    batch.status = 'submitted'
                    batch.submitted_at = timezone.now()
                    batch.save()
                    # Notify registrar
                    try:
                        from notifications.utils import notify
                        from accounts.models import User
                        for reg_user in User.objects.filter(role='registrar'):
                            notify(reg_user, 'result',
                                f'Results submitted: {course.code}',
                                f'{request.user.get_full_name()} submitted results for {course.title}',
                                '/results/registrar/')
                    except Exception: pass
                    messages.success(request, f'✅ Results for {course.code} submitted to Registrar!')
                    return redirect('results:lecturer_courses')
            else:
                messages.success(request, '✅ Scores saved as draft.')
        # Refresh existing
        existing = {
            r.student_id: r for r in CourseResult.objects.filter(
                course=course, semester=semester
            )
        }

    return render(request, 'results/lecturer/enter_results.html', {
        'course': course, 'semester': semester, 'session': session,
        'students': students, 'existing': existing, 'batch': batch,
    })


# ── REGISTRAR VIEWS ────────────────────────────────────────────────────────────

@login_required
def registrar_results(request):
    """Registrar sees all submitted result batches."""
    status_filter = request.GET.get('status','submitted')
    batches = ResultBatch.objects.select_related(
        'course','semester','lecturer'
    ).order_by('-submitted_at')
    if status_filter:
        batches = batches.filter(status=status_filter)
    counts = {
        'draft':     ResultBatch.objects.filter(status='draft').count(),
        'submitted': ResultBatch.objects.filter(status='submitted').count(),
        'approved':  ResultBatch.objects.filter(status='approved').count(),
        'rejected':  ResultBatch.objects.filter(status='rejected').count(),
    }
    return render(request, 'results/registrar/list.html', {
        'batches': batches, 'counts': counts, 'status_filter': status_filter,
    })


@login_required
def registrar_batch_detail(request, batch_id):
    """Registrar reviews a batch of results."""
    batch   = get_object_or_404(ResultBatch, pk=batch_id)
    results = CourseResult.objects.filter(
        course=batch.course, semester=batch.semester
    ).select_related('student','student__user').order_by('student__reg_number')

    # Summary stats
    grades = {}
    for r in results:
        grades[r.grade] = grades.get(r.grade, 0) + 1

    return render(request, 'results/registrar/detail.html', {
        'batch': batch, 'results': results, 'grades': grades,
    })


@login_required
def approve_batch(request, batch_id):
    batch = get_object_or_404(ResultBatch, pk=batch_id)
    if request.method == 'POST':
        with transaction.atomic():
            batch.status      = 'approved'
            batch.approved_by = request.user
            batch.approved_at = timezone.now()
            batch.save()
            CourseResult.objects.filter(
                course=batch.course, semester=batch.semester
            ).update(status='approved', approved_by=request.user, approved_at=timezone.now())
        # Notify lecturer
        try:
            from notifications.utils import notify
            notify(batch.lecturer, 'result',
                f'Results Approved: {batch.course.code}',
                f'Your results for {batch.course.code} have been approved by the Registrar.',
                '/results/my-courses/')
        except Exception: pass
        messages.success(request, f'✅ Results for {batch.course.code} approved and published to students!')
    return redirect('results:registrar_results')


@login_required
def reject_batch(request, batch_id):
    batch = get_object_or_404(ResultBatch, pk=batch_id)
    if request.method == 'POST':
        reason = request.POST.get('reason','')
        batch.status        = 'rejected'
        batch.reject_reason = reason
        batch.save()
        CourseResult.objects.filter(
            course=batch.course, semester=batch.semester
        ).update(status='rejected')
        try:
            from notifications.utils import notify
            notify(batch.lecturer, 'result',
                f'Results Rejected: {batch.course.code}',
                f'Reason: {reason}. Please correct and resubmit.',
                '/results/my-courses/')
        except Exception: pass
        messages.warning(request, f'Results for {batch.course.code} rejected.')
    return redirect('results:registrar_results')


# ── STUDENT VIEWS ─────────────────────────────────────────────────────────────

@login_required
def student_results(request):
    """Student sees their approved results with GPA/CGPA."""
    try:
        student = request.user.student
    except Exception:
        return redirect('student_dashboard')

    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()

    # All approved results grouped by semester
    all_results = CourseResult.objects.filter(
        student=student, status='approved'
    ).select_related('course','semester','session').order_by(
        'session__name','semester__name','course__code'
    )

    # Group by semester
    from collections import defaultdict
    semester_groups = defaultdict(list)
    for r in all_results:
        key = f"{r.session.name} — {r.semester.name}"
        semester_groups[key].append(r)

    # Calculate GPA per semester and CGPA
    semester_data = []
    cgpa_total_points = 0
    cgpa_total_units  = 0

    for label, results in semester_groups.items():
        total_points = sum(float(r.grade_point or 0) * r.course.unit for r in results)
        total_units  = sum(r.course.unit for r in results)
        gpa = round(total_points / total_units, 2) if total_units else 0
        cgpa_total_points += total_points
        cgpa_total_units  += total_units
        semester_data.append({
            'label': label, 'results': results,
            'total_units': total_units,
            'total_points': round(total_points, 2),
            'gpa': gpa,
        })

    cgpa = round(cgpa_total_points / cgpa_total_units, 2) if cgpa_total_units else 0

    # Diploma classification
    if   cgpa >= 4.50: degree_class = "Distinction"
    elif cgpa >= 3.50: degree_class = "Upper Credit"
    elif cgpa >= 2.50: degree_class = "Lower Credit"
    elif cgpa >= 1.00: degree_class = "Pass"
    else:              degree_class = "Fail"

    # Current semester pending results
    current_results = CourseResult.objects.filter(
        student=student, semester=semester
    ).select_related('course')

    return render(request, 'results/student/my_results.html', {
        'student': student,
        'semester_data': semester_data,
        'degree_class': degree_class,
        'cgpa': cgpa,
        'cgpa_total_units': cgpa_total_units,
        'current_results': current_results,
        'semester': semester,
    })

@login_required
def download_scoresheet(request, course_id):
    """Lecturer downloads score sheet PDF for a course."""
    course   = get_object_or_404(Course, pk=course_id)
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()

    results = CourseResult.objects.filter(
        course=course, semester=semester
    ).select_related('student','student__user').order_by('student__reg_number')

    batch = ResultBatch.objects.filter(
        lecturer=request.user, course=course, semester=semester
    ).first()

    from documents.views import render_pdf
    return render_pdf(
        'results/lecturer/scoresheet_pdf.html',
        {
            'course': course, 'semester': semester, 'session': session,
            'results': results, 'batch': batch,
            'lecturer': request.user,
            'total_students': results.count(),
            'passed': results.filter(grade__in=['A','B','C','D','E']).count(),
            'failed':  results.filter(grade='F').count(),
        },
        f'Scoresheet_{course.code}_{semester}.pdf'
    )


@login_required
def recall_batch(request, batch_id):
    """Registrar recalls an approved result batch for editing."""
    batch = get_object_or_404(ResultBatch, pk=batch_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        with transaction.atomic():
            batch.status        = 'draft'
            batch.approved_by   = None
            batch.approved_at   = None
            batch.reject_reason = reason
            batch.save()
            CourseResult.objects.filter(
                course=batch.course, semester=batch.semester
            ).update(status='draft', approved_by=None, approved_at=None)
        # Notify lecturer
        try:
            from notifications.utils import notify
            notify(batch.lecturer, 'result',
                f'Result Recalled: {batch.course.code}',
                f'Registrar has recalled your results for {batch.course.code}. Reason: {reason}. Please correct and resubmit.',
                '/results/my-courses/')
        except Exception:
            pass
        from django.contrib import messages
        messages.warning(request, f'Results for {batch.course.code} recalled and returned to draft for editing.')
    return redirect('results:registrar_results')
