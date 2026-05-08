import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from students.models import Student
from core.models import Session, Semester
from .models import FeePayment

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

@role_required('student')
def make_payment(request):
    student = get_object_or_404(Student, user=request.user)
    session = student.current_session
    if request.method == 'POST':
        payment_type = request.POST['payment_type']
        semester_id = request.POST.get('semester')
        amount = 50000 if payment_type == 'session' else 25000
        semester = Semester.objects.get(pk=semester_id) if semester_id else None
        already = FeePayment.objects.filter(
            student=student, session=session,
            payment_type=payment_type, status__in=['pending', 'approved']
        ).exists()
        if already:
            messages.warning(request, 'You already have a payment request for this period.')
            return redirect('my_payments')
        FeePayment.objects.create(
            student=student, session=session, semester=semester,
            payment_type=payment_type, amount=amount,
            receipt_number=f'RCP-{uuid.uuid4().hex[:8].upper()}'
        )
        messages.success(request, f'Payment request of ₦{amount:,} submitted.')
        return redirect('my_payments')
    semesters = Semester.objects.filter(session=session) if session else []
    return render(request, 'fees/make_payment.html', {
        'student': student, 'session': session, 'semesters': semesters,
    })

@role_required('student')
def my_payments(request):
    student = get_object_or_404(Student, user=request.user)
    payments = FeePayment.objects.filter(student=student).order_by('-date_requested')
    return render(request, 'fees/my_payments.html', {'student': student, 'payments': payments})

@role_required('bursar', 'admin')
def bursar_dashboard(request):
    pending = FeePayment.objects.filter(status='pending').select_related('student__user', 'session')
    approved = FeePayment.objects.filter(status='approved').order_by('-date_approved')[:20]
    return render(request, 'fees/bursar_dashboard.html', {
        'pending': pending, 'approved': approved,
    })

@role_required('bursar', 'admin')
def approve_payment(request, pk):
    payment = get_object_or_404(FeePayment, pk=pk)
    payment.status = 'approved'
    payment.approved_by = request.user
    payment.date_approved = timezone.now()
    payment.save()
    messages.success(request, f'Payment {payment.receipt_number} approved.')
    return redirect('bursar_dashboard')

@role_required('bursar', 'admin')
def reject_payment(request, pk):
    payment = get_object_or_404(FeePayment, pk=pk)
    payment.status = 'rejected'
    payment.save()
    messages.warning(request, f'Payment {payment.receipt_number} rejected.')
    return redirect('bursar_dashboard')

    from django.shortcuts import get_object_or_404
from django.http import FileResponse
from students.models import Student
from .models import Payment

def download_fee_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    student = get_object_or_404(Student, user=payment.student)
    return FileResponse(buffer, as_attachment=True, filename=f"{student.matric_number}_receipt.pdf")