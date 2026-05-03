import base64, uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
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
                messages.error(request, 'Access denied.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@role_required('admin', 'academic_officer')
def admin_dashboard(request):
    context = {
        'total_students': Student.objects.filter(status='active').count(),
        'total_programmes': Programme.objects.count(),
        'pending_payments': FeePayment.objects.filter(status='pending').count(),
        'active_session': Session.objects.filter(is_active=True).first(),
        'active_semester': Semester.objects.filter(is_active=True).first(),
        'recent_students': Student.objects.order_by('-date_enrolled')[:5],
    }
    return render(request, 'students/admin_dashboard.html', context)

@role_required('admin', 'academic_officer')
def student_list(request):
    students = Student.objects.select_related('user', 'programme', 'current_session').all()
    programmes = Programme.objects.all()
    if request.GET.get('programme'):
        students = students.filter(programme__id=request.GET['programme'])
    if request.GET.get('status'):
        students = students.filter(status=request.GET['status'])
    return render(request, 'students/student_list.html', {
        'students': students, 'programmes': programmes,
    })

@role_required('admin')
def add_student(request):
    if request.method == 'POST':
        first_name   = request.POST['first_name']
        last_name    = request.POST['last_name']
        email        = request.POST['email']
        reg_number   = request.POST['reg_number']
        programme_id = request.POST['programme']
        session_id   = request.POST['session']
        semester_id  = request.POST['semester']
        if User.objects.filter(username=reg_number).exists():
            messages.error(request, 'Registration number already exists.')
            return redirect('add_student')
        user = User.objects.create_user(
            username=reg_number, password=reg_number,
            first_name=first_name, last_name=last_name,
            email=email, role='student'
        )
        Student.objects.create(
            user=user, reg_number=reg_number,
            programme=Programme.objects.get(pk=programme_id),
            current_session=Session.objects.get(pk=session_id),
            current_semester=Semester.objects.get(pk=semester_id),
        )
        messages.success(request, f'Student {first_name} {last_name} added successfully.')
        return redirect('student_list')
    return render(request, 'students/add_student.html', {
        'programmes': Programme.objects.all(),
        'sessions': Session.objects.all(),
        'semesters': Semester.objects.all(),
    })

@role_required('admin', 'academic_officer')
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    registrations = CourseRegistration.objects.filter(student=student).prefetch_related('courses')
    payments = FeePayment.objects.filter(student=student)
    return render(request, 'students/student_detail.html', {
        'student': student, 'registrations': registrations, 'payments': payments,
    })

@role_required('admin')
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.user.delete()
    messages.success(request, 'Student deleted.')
    return redirect('student_list')

@role_required('admin')
def migrate_students(request):
    if request.method == 'POST':
        active_session = Session.objects.filter(is_active=True).first()
        if not active_session:
            messages.error(request, 'No active session found.')
            return redirect('admin_dashboard')
        count = Student.objects.filter(status='active').update(current_session=active_session)
        messages.success(request, f'{count} students migrated to {active_session}.')
    return redirect('admin_dashboard')

@role_required('student')
def student_dashboard(request):
    student = get_object_or_404(Student, user=request.user)
    active_semester = Semester.objects.filter(is_active=True).first()
    registration = None
    if active_semester:
        registration = CourseRegistration.objects.filter(
            student=student, semester=active_semester
        ).first()
    payments = FeePayment.objects.filter(student=student).order_by('-date_requested')[:5]
    return render(request, 'students/student_dashboard.html', {
        'student': student,
        'active_semester': active_semester,
        'registration': registration,
        'payments': payments,
    })

@role_required('student')
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)
    return render(request, 'students/profile.html', {'student': student})

@role_required('student')
def upload_photo(request):
    student = get_object_or_404(Student, user=request.user)
    if request.method == 'POST':
        webcam_data = request.POST.get('webcam_data')
        file_upload = request.FILES.get('photo_file')
        if webcam_data:
            fmt, imgstr = webcam_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
            student.photo = data
            student.save()
            messages.success(request, 'Photo saved from webcam.')
        elif file_upload:
            student.photo = file_upload
            student.save()
            messages.success(request, 'Photo uploaded successfully.')
        else:
            messages.error(request, 'No photo provided.')
        return redirect('student_profile')
    return render(request, 'students/upload_photo.html', {'student': student})

@role_required('student')
def register_courses(request):
    student = get_object_or_404(Student, user=request.user)
    active_semester = Semester.objects.filter(is_active=True).first()
    if not active_semester:
        messages.error(request, 'No active semester. Contact admin.')
        return redirect('student_dashboard')
    paid = FeePayment.objects.filter(
        student=student, session=student.current_session, status='approved'
    ).exists()
    if not paid:
        messages.error(request, 'Please pay your fees before registering courses.')
        return redirect('student_dashboard')
    existing_reg = CourseRegistration.objects.filter(
        student=student, semester=active_semester
    ).first()
    sem_num = 1 if active_semester.name == 'first' else 2
    if student.programme.level == 'diploma2':
        sem_num += 2
    available_courses = Course.objects.filter(
        programme=student.programme, semester_number=sem_num
    )
    if request.method == 'POST':
        selected_ids = request.POST.getlist('courses')
        reg = existing_reg or CourseRegistration.objects.create(
            student=student, semester=active_semester
        )
        reg.courses.set(selected_ids)
        reg.save()
        messages.success(request, 'Courses registered successfully.')
        return redirect('my_courses')
    return render(request, 'students/register_courses.html', {
        'student': student, 'courses': available_courses,
        'existing_reg': existing_reg, 'active_semester': active_semester,
    })

@role_required('student')
def my_courses(request):
    student = get_object_or_404(Student, user=request.user)
    active_semester = Semester.objects.filter(is_active=True).first()
    registration = CourseRegistration.objects.filter(
        student=student, semester=active_semester
    ).prefetch_related('courses').first()
    return render(request, 'students/my_courses.html', {
        'student': student, 'registration': registration, 'active_semester': active_semester,
    })
@role_required('admin', 'academic_officer')
def semester_result(request):
    from academics.models import Department, Programme, Course
    departments = Department.objects.all()
    programmes = Programme.objects.all()
    sessions = Session.objects.all()
    semesters = Semester.objects.all()

    result_data = None
    selected = {}

    if request.GET.get('programme') and request.GET.get('semester'):
        prog_id = request.GET.get('programme')
        sem_id = request.GET.get('semester')
        programme = Programme.objects.get(pk=prog_id)
        semester = Semester.objects.get(pk=sem_id)

        registrations = CourseRegistration.objects.filter(
            semester=semester,
            student__programme=programme,
            student__status='active'
        ).select_related('student__user').prefetch_related('courses')

        courses = Course.objects.filter(
            programme=programme,
            semester_number=1 if semester.name == 'first' else 2
        ).order_by('code')

        result_rows = []
        for reg in registrations:
            result_rows.append({
                'student': reg.student,
                'courses': courses,
                'reg': reg,
            })

        result_data = {
            'programme': programme,
            'semester': semester,
            'courses': courses,
            'rows': result_rows,
        }
        selected = {'programme': prog_id, 'semester': sem_id}

    return render(request, 'students/semester_result.html', {
        'departments': departments,
        'programmes': programmes,
        'sessions': sessions,
        'semesters': semesters,
        'result_data': result_data,
        'selected': selected,
    })