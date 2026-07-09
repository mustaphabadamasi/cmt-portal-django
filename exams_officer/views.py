from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from students.models import Student, CourseRegistration
from academics.models import Programme
from core.models import Semester, Session
from documents.views import render_pdf
import io


def exams_officer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/accounts/login/')
        if request.user.role not in ('exams_officer', 'registrar', 'admin'):
            messages.error(request, 'Access denied.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
@exams_officer_required
def dashboard(request):
    semester    = Semester.objects.filter(is_active=True).first()
    session     = Session.objects.filter(is_active=True).first()
    programmes  = Programme.objects.all().order_by('name')

    # Filters
    prog_id  = request.GET.get('programme')
    level    = request.GET.get('level')
    sem_id   = request.GET.get('semester')

    students = Student.objects.filter(
        status='active'
    ).select_related('user', 'programme').order_by(
        'programme__name', 'reg_number'
    )

    if prog_id:
        students = students.filter(programme_id=prog_id)
    if level:
        students = students.filter(level=level)
    if sem_id:
        semester = Semester.objects.filter(pk=sem_id).first()

    # Add registration status to each student
    student_data = []
    for s in students:
        reg = CourseRegistration.objects.filter(
            student=s, semester=semester
        ).first()
        student_data.append({
            'student':      s,
            'registered':   bool(reg),
            'course_count': reg.courses.count() if reg else 0,
        })

    semesters = Semester.objects.all().order_by('name')

    return render(request, 'exams_officer/dashboard.html', {
        'student_data': student_data,
        'semester':     semester,
        'session':      session,
        'programmes':   programmes,
        'semesters':    semesters,
        'total':        len(student_data),
        'registered':   sum(1 for d in student_data if d['registered']),
        'selected_prog': prog_id,
        'selected_level': level,
        'selected_sem':  sem_id,
    })


@login_required
@exams_officer_required
def print_exam_card(request, student_id):
    """Print single student exam card."""
    student  = get_object_or_404(Student, pk=student_id)
    semester = Semester.objects.filter(is_active=True).first()
    reg = CourseRegistration.objects.filter(
        student=student, semester=semester
    ).prefetch_related('courses').first()

    import base64, os
    from django.conf import settings

    def img_b64(path):
        try:
            ext = os.path.splitext(path)[1].lower().replace('.','')
            if ext == 'jpg': ext = 'jpeg'
            with open(path,'rb') as f:
                return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
        except: return None

    base = str(settings.BASE_DIR)
    cmt_logo = fud_logo = photo_uri = None
    for d in ['staticfiles/images','static/images']:
        dp = os.path.join(base, d)
        if not os.path.exists(dp): continue
        for f in os.listdir(dp):
            fl = f.lower()
            if 'cmt' in fl: cmt_logo = img_b64(os.path.join(dp,f))
            if 'fud' in fl: fud_logo = img_b64(os.path.join(dp,f))

    if student.photo:
        try: photo_uri = img_b64(student.photo.path)
        except: pass

    safe_reg = student.reg_number.replace('/','_')
    return render_pdf('exams_officer/exam_card_pdf.html', {
        'student': student, 'semester': semester,
        'registration': reg, 'cmt_logo': cmt_logo,
        'fud_logo': fud_logo, 'photo_uri': photo_uri,
    }, f'ExamCard_{safe_reg}.pdf')


@login_required
@exams_officer_required
def print_course_form(request, student_id):
    """Print single student course registration form."""
    student  = get_object_or_404(Student, pk=student_id)
    semester = Semester.objects.filter(is_active=True).first()
    session  = Session.objects.filter(is_active=True).first()
    reg = CourseRegistration.objects.filter(
        student=student, semester=semester
    ).prefetch_related('courses').first()

    import base64, os
    from django.conf import settings

    def img_b64(path):
        try:
            ext = os.path.splitext(path)[1].lower().replace('.','')
            if ext == 'jpg': ext = 'jpeg'
            with open(path,'rb') as f:
                return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
        except: return None

    base = str(settings.BASE_DIR)
    cmt_logo = fud_logo = photo_uri = None
    for d in ['staticfiles/images','static/images']:
        dp = os.path.join(base, d)
        if not os.path.exists(dp): continue
        for f in os.listdir(dp):
            fl = f.lower()
            if 'cmt' in fl: cmt_logo = img_b64(os.path.join(dp,f))
            if 'fud' in fl: fud_logo = img_b64(os.path.join(dp,f))

    if student.photo:
        try: photo_uri = img_b64(student.photo.path)
        except: pass

    safe_reg = student.reg_number.replace('/','_')
    return render_pdf('exams_officer/course_form_pdf.html', {
        'student': student, 'semester': semester, 'session': session,
        'registration': reg, 'cmt_logo': cmt_logo,
        'fud_logo': fud_logo, 'photo_uri': photo_uri,
    }, f'CourseForm_{safe_reg}.pdf')


@login_required
@exams_officer_required
def bulk_exam_cards(request):
    """Bulk print ALL exam cards as one PDF."""
    semester   = Semester.objects.filter(is_active=True).first()
    prog_id    = request.GET.get('programme')
    level      = request.GET.get('level')

    students = Student.objects.filter(status='active').select_related(
        'user','programme').order_by('programme__name','reg_number')
    if prog_id:  students = students.filter(programme_id=prog_id)
    if level:    students = students.filter(level=level)

    import base64, os
    from django.conf import settings

    def img_b64(path):
        try:
            ext = os.path.splitext(path)[1].lower().replace('.','')
            if ext == 'jpg': ext = 'jpeg'
            with open(path,'rb') as f:
                return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
        except: return None

    base = str(settings.BASE_DIR)
    cmt_logo = fud_logo = None
    for d in ['staticfiles/images','static/images']:
        dp = os.path.join(base,d)
        if not os.path.exists(dp): continue
        for f in os.listdir(dp):
            fl = f.lower()
            if 'cmt' in fl: cmt_logo = img_b64(os.path.join(dp,f))
            if 'fud' in fl: fud_logo = img_b64(os.path.join(dp,f))

    student_data = []
    for s in students:
        reg = CourseRegistration.objects.filter(
            student=s, semester=semester
        ).prefetch_related('courses').first()
        if not reg: continue
        photo_uri = None
        if s.photo:
            try: photo_uri = img_b64(s.photo.path)
            except: pass
        student_data.append({
            'student': s, 'registration': reg, 'photo_uri': photo_uri
        })

    if not student_data:
        messages.warning(request, 'No registered students found for selected filters.')
        return redirect('exams_officer:dashboard')

    return render_pdf('exams_officer/bulk_exam_cards_pdf.html', {
        'student_data': student_data,
        'semester': semester,
        'cmt_logo': cmt_logo,
        'fud_logo': fud_logo,
        'total': len(student_data),
    }, f'BulkExamCards_{semester}.pdf')


@login_required
@exams_officer_required
def bulk_course_forms(request):
    """Bulk print ALL course registration forms as one PDF."""
    semester  = Semester.objects.filter(is_active=True).first()
    session   = Session.objects.filter(is_active=True).first()
    prog_id   = request.GET.get('programme')
    level     = request.GET.get('level')

    students = Student.objects.filter(status='active').select_related(
        'user','programme').order_by('programme__name','reg_number')
    if prog_id: students = students.filter(programme_id=prog_id)
    if level:   students = students.filter(level=level)

    import base64, os
    from django.conf import settings

    def img_b64(path):
        try:
            ext = os.path.splitext(path)[1].lower().replace('.','')
            if ext == 'jpg': ext = 'jpeg'
            with open(path,'rb') as f:
                return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
        except: return None

    base = str(settings.BASE_DIR)
    cmt_logo = fud_logo = None
    for d in ['staticfiles/images','static/images']:
        dp = os.path.join(base,d)
        if not os.path.exists(dp): continue
        for f in os.listdir(dp):
            fl = f.lower()
            if 'cmt' in fl: cmt_logo = img_b64(os.path.join(dp,f))
            if 'fud' in fl: fud_logo = img_b64(os.path.join(dp,f))

    student_data = []
    for s in students:
        reg = CourseRegistration.objects.filter(
            student=s, semester=semester
        ).prefetch_related('courses').first()
        if not reg: continue
        photo_uri = None
        if s.photo:
            try: photo_uri = img_b64(s.photo.path)
            except: pass
        student_data.append({
            'student': s, 'registration': reg, 'photo_uri': photo_uri
        })

    if not student_data:
        messages.warning(request, 'No registered students found.')
        return redirect('exams_officer:dashboard')

    return render_pdf('exams_officer/bulk_course_forms_pdf.html', {
        'student_data': student_data,
        'semester': semester, 'session': session,
        'cmt_logo': cmt_logo, 'fud_logo': fud_logo,
        'total': len(student_data),
    }, f'BulkCourseForms_{semester}.pdf')
