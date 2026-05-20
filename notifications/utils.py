"""
Utility functions for creating notifications.
Import and call these from any view that needs to send notifications.
"""
from .models import Notification


def notify(recipient, ntype, title, message='', link=''):
    """Create a single notification for one user."""
    return Notification.objects.create(
        recipient=recipient, type=ntype,
        title=title, message=message, link=link,
    )


def notify_course_students(course, semester, ntype, title, message='', link=''):
    """
    Notify all students registered for course+semester.
    Returns count of notifications created.
    """
    from students.models import CourseRegistration
    student_user_ids = set()
    for reg in CourseRegistration.objects.filter(
        courses=course, semester=semester
    ).select_related('student__user'):
        student_user_ids.add(reg.student.user_id)

    bulk = [
        Notification(recipient_id=uid, type=ntype,
                     title=title, message=message, link=link)
        for uid in student_user_ids
    ]
    Notification.objects.bulk_create(bulk)
    return len(bulk)


def check_deadlines(student):
    """
    Called on page load for students.
    Creates deadline notifications for assignments due within 24 h
    if no notification has been sent yet.
    """
    from django.utils import timezone
    try:
        from lecturers.models import Assignment
        from students.models import CourseRegistration
    except ImportError:
        return

    now      = timezone.now()
    in_24h   = now + timezone.timedelta(hours=24)

    # Courses the student is registered in
    reg_course_ids = []
    for reg in CourseRegistration.objects.filter(student=student):
        reg_course_ids.extend(reg.courses.values_list('id', flat=True))

    # Assignments due in next 24 hours
    upcoming = Assignment.objects.filter(
        course_id__in=reg_course_ids,
        is_published=True,
        deadline_individual__gt=now,
        deadline_individual__lte=in_24h,
    )

    for asn in upcoming:
        key = f'deadline-{asn.pk}'
        already = Notification.objects.filter(
            recipient=student.user,
            type='deadline',
            link__contains=str(asn.pk),
        ).exists()
        if not already:
            Notification.objects.create(
                recipient=student.user,
                type='deadline',
                title=f'⏰ Deadline Soon: {asn.title}',
                message=(f'{asn.course.code} assignment due '
                         f'{asn.deadline_individual.strftime("%d %b %Y %I:%M %p")}'),
                link=f'/lecturers/my-assignments/',
            )
