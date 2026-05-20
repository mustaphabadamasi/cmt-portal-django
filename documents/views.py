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
    import os
    from django.conf import settings as djs

    def link_callback(uri, rel):
        if uri.startswith(djs.STATIC_URL):
            rel_path = uri[len(djs.STATIC_URL):]
            # Check STATIC_ROOT
            path = os.path.join(djs.STATIC_ROOT, rel_path)
            if os.path.isfile(path):
                return path
            # Check STATICFILES_DIRS
            for d in getattr(djs, "STATICFILES_DIRS", []):
                path = os.path.join(d, rel_path)
                if os.path.isfile(str(path)):
                    return str(path)
        if uri.startswith(djs.MEDIA_URL):
            path = os.path.join(djs.MEDIA_ROOT, uri[len(djs.MEDIA_URL):])
            if os.path.isfile(path):
                return path
        return uri

    html = render_to_string(template, context)
    buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=buffer, link_callback=link_callback)
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