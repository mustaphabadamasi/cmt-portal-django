from .jaas_token import generate_jaas_token
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import LiveClass, ClassAttendance
from academics.models import Course
from core.models import Semester
from lecturers.models import Lecturer


# ─── LECTURER VIEWS ────────────────────────────────────────────────────────────

@login_required
def lecturer_class_list(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    classes  = LiveClass.objects.filter(lecturer=lecturer).select_related('course', 'semester')
    return render(request, 'live_classes/lecturer/list.html', {
        'classes': classes, 'lecturer': lecturer
    })


@login_required
def lecturer_class_create(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    # Only assigned courses
    from lecturers.models import LecturerCourse
    assigned_ids = LecturerCourse.objects.filter(
        lecturer=lecturer, is_active=True
    ).values_list('course_id', flat=True)
    courses   = Course.objects.filter(id__in=assigned_ids).order_by('code')
    semesters = Semester.objects.all().order_by('-id')

    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        desc       = request.POST.get('description', '').strip()
        course_id  = request.POST.get('course')
        sem_id     = request.POST.get('semester')
        sched_start = request.POST.get('scheduled_start')
        sched_end   = request.POST.get('scheduled_end')

        if not all([title, course_id, sem_id, sched_start, sched_end]):
            messages.error(request, 'All fields are required.')
        else:
            course   = get_object_or_404(Course,   id=course_id)
            semester = get_object_or_404(Semester, id=sem_id)
            lc = LiveClass.objects.create(
                title=title, description=desc,
                course=course, semester=semester,
                lecturer=lecturer,
                scheduled_start=sched_start,
                scheduled_end=sched_end,
            )
            messages.success(request, f'"{lc.title}" scheduled successfully!')
            return redirect('live_classes:lecturer_detail', pk=lc.pk)

    return render(request, 'live_classes/lecturer/create.html', {
        'courses': courses, 'semesters': semesters, 'lecturer': lecturer
    })


@login_required
def lecturer_class_detail(request, pk):
    lecturer  = get_object_or_404(Lecturer, user=request.user)
    lc        = get_object_or_404(LiveClass, pk=pk, lecturer=lecturer)
    attendance = lc.attendance.select_related('student__user').order_by('joined_at')
    jaas_token = None
    if lc.status == 'live':
        jaas_token = generate_jaas_token(request.user, lc.jitsi_room_name, is_moderator=True)
    display_name = request.user.get_full_name() or request.user.username
    return render(request, 'live_classes/lecturer/detail.html', {
        'lc': lc, 'lecturer': lecturer, 'attendance': attendance,
        'jaas_token': jaas_token, 'room_name': lc.jitsi_room_name,
        'display_name': display_name,
    })


@login_required
def lecturer_class_start(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    lc       = get_object_or_404(LiveClass, pk=pk, lecturer=lecturer)
    if request.method == 'POST':
        lc.status       = 'live'
        lc.actual_start = timezone.now()
        lc.save()
        messages.success(request, f'"{lc.title}" is now LIVE! Students can join.')
        try:
            from notifications.utils import notify_course_students
            notify_course_students(
                course=lc.course, semester=lc.semester,
                ntype='live_class',
                title=f'🔴 LIVE NOW: {lc.title}',
                message=f'{lc.course.code} live class has started — join now!',
                link='/live-classes/student/',
            )
        except Exception:
            pass
    return redirect('live_classes:lecturer_detail', pk=pk)


@login_required
def lecturer_class_end(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    lc       = get_object_or_404(LiveClass, pk=pk, lecturer=lecturer)
    if request.method == 'POST':
        lc.status     = 'ended'
        lc.actual_end = timezone.now()
        lc.save()
        messages.success(request, f'"{lc.title}" has ended.')
    return redirect('live_classes:lecturer_detail', pk=pk)


@login_required
def lecturer_class_cancel(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    lc       = get_object_or_404(LiveClass, pk=pk, lecturer=lecturer)
    if request.method == 'POST':
        lc.status = 'cancelled'
        lc.save()
        messages.success(request, f'"{lc.title}" has been cancelled.')
    return redirect('live_classes:lecturer_detail', pk=pk)


@login_required
def lecturer_class_delete(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    lc       = get_object_or_404(LiveClass, pk=pk, lecturer=lecturer)
    if request.method == 'POST':
        title = lc.title
        lc.delete()
        messages.success(request, f'"{title}" deleted.')
        return redirect('live_classes:lecturer_list')
    return render(request, 'live_classes/lecturer/delete_confirm.html', {'lc': lc})


# ─── STUDENT VIEWS ─────────────────────────────────────────────────────────────

@login_required
def student_class_list(request):
    from students.models import Student, CourseRegistration
    student = get_object_or_404(Student, user=request.user)

    # Courses the student is registered for
    reg_course_ids = []
    for reg in CourseRegistration.objects.filter(student=student):
        reg_course_ids.extend(reg.courses.values_list('id', flat=True))
    reg_course_ids = list(set(reg_course_ids))

    classes = LiveClass.objects.filter(
        course_id__in=reg_course_ids
    ).exclude(status='cancelled').select_related('course', 'lecturer__user').order_by('-scheduled_start')

    attended_ids = list(
        ClassAttendance.objects.filter(student=student).values_list('live_class_id', flat=True)
    )

    return render(request, 'live_classes/student/list.html', {
        'classes': classes, 'student': student, 'attended_ids': attended_ids
    })


@login_required
def student_class_join(request, pk):
    from students.models import Student
    lc      = get_object_or_404(LiveClass, pk=pk)
    student = get_object_or_404(Student, user=request.user)

    if lc.status != 'live':
        messages.error(request, 'This class is not currently live.')
        return redirect('live_classes:student_list')

    # Record attendance (get_or_create so refresh doesn't double-count)
    ClassAttendance.objects.get_or_create(live_class=lc, student=student)

    display_name = request.user.get_full_name() or request.user.username
    jaas_token   = generate_jaas_token(request.user, lc.jitsi_room_name, is_moderator=False)

    return render(request, 'live_classes/student/join.html', {
        'lc': lc, 'student': student, 'display_name': display_name,
        'jaas_token': jaas_token, 'room_name': lc.jitsi_room_name
    })


@login_required
def student_class_leave(request, pk):
    """Record leave time when student exits Jitsi"""
    from students.models import Student
    student = get_object_or_404(Student, user=request.user)
    attendance = ClassAttendance.objects.filter(
        live_class_id=pk, student=student, left_at__isnull=True
    ).first()
    if attendance:
        attendance.left_at = timezone.now()
        attendance.save()
    return redirect('live_classes:student_list')
