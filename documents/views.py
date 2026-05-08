from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa
import io
from students.models import Student
from academics.models import CourseRegistration
from fees.models import FeePayment
from core.models import Semester

def render_pdf(template, context, filename):
    html = render_to_string(template, context)
    buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=buffer)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def exam_card(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    semester = Semester.objects.filter(is_active=True).first()
    registration = CourseRegistration.objects.filter(
        student=student, semester=semester
    ).prefetch_related('courses').first()
    return render_pdf('documents/exam_card.html', {
        'student': student, 'registration': registration, 'semester': semester, 'request': request,
    }, f'exam_card_{student.reg_number}.pdf')

@login_required
def course_reg_form(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    semester = Semester.objects.filter(is_active=True).first()
    registration = CourseRegistration.objects.filter(
        student=student, semester=semester
    ).prefetch_related('courses').first()
    return render_pdf('documents/course_reg_form.html', {
        'student': student, 'registration': registration, 'semester': semester, 'request': request,
    }, f'course_reg_{student.reg_number}.pdf')

@login_required
def payment_receipt(request, payment_id):
    payment = get_object_or_404(FeePayment, pk=payment_id)
    return render_pdf('documents/receipt.html', {
        'payment': payment, 'student': payment.student, 'request': request,
    }, f'receipt_{payment.receipt_number}.pdf')