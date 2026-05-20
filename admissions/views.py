from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Application, OLevelResult, OLevelSubject, SchoolFeeInvoice, SUBJECTS, GRADE_CHOICES
from academics.models import Programme
from core.models import Session

BANKS = ["Access Bank","First Bank","GT Bank","UBA","Zenith Bank",
         "Ecobank","Fidelity Bank","FCMB","Keystone Bank",
         "Polaris Bank","Sterling Bank","Union Bank","Wema Bank","Other"]

def apply(request):
    programmes = Programme.objects.all().order_by("name")
    sessions   = Session.objects.filter(accepts_applications=True).order_by("-name")
    subjects   = SUBJECTS
    grades     = GRADE_CHOICES
    if request.method == "POST":
        p = request.POST
        required = ["first_name","last_name","date_of_birth","gender",
                    "phone","email","address","state_of_origin","lga",
                    "programme","session","exam_type","exam_year","exam_number",
                    "app_fee_reference","app_fee_bank","app_fee_date"]
        if any(not p.get(f,"").strip() for f in required):
            messages.error(request, "Please fill all required fields.")
            return render(request, "admissions/apply.html", locals())
        app = Application.objects.create(
            first_name=p["first_name"].strip(),
            last_name=p["last_name"].strip(),
            middle_name=p.get("middle_name","").strip(),
            date_of_birth=p["date_of_birth"],
            gender=p["gender"],
            nationality=p.get("nationality","Nigerian"),
            state_of_origin=p["state_of_origin"],
            lga=p["lga"],
            religion=p.get("religion",""),
            phone=p["phone"],
            email=p["email"],
            address=p["address"],
            programme=Programme.objects.get(pk=p["programme"]),
            session=Session.objects.get(pk=p["session"]),
            photo=request.FILES.get("photo"),
            app_fee_reference=p["app_fee_reference"].strip(),
            app_fee_bank=p["app_fee_bank"],
            app_fee_date=p["app_fee_date"],
            status="app_fee_submitted",
        )
        result = OLevelResult.objects.create(
            application=app,
            exam_type=p["exam_type"],
            exam_year=p["exam_year"],
            exam_number=p["exam_number"],
            sitting=p.get("sitting","1st"),
        )
        for s, g in zip(p.getlist("subject[]"), p.getlist("grade[]")):
            if s and g:
                OLevelSubject.objects.get_or_create(result=result, subject=s, defaults={"grade":g})
        return redirect("admissions:submitted", pk=app.pk)
    return render(request, "admissions/apply.html", locals())

def submitted(request, pk):
    app = get_object_or_404(Application, pk=pk)
    return render(request, "admissions/submitted.html", {"app": app})

def check_status(request):
    app = None
    if request.method == "POST":
        num = request.POST.get("application_number","").strip()
        try:
            app = Application.objects.get(application_number=num)
        except Application.DoesNotExist:
            messages.error(request, "Application number not found.")
    return render(request, "admissions/check_status.html", {"app": app})

@login_required
def generate_invoice(request):
    try:
        student = request.user.student
        app     = student.application
    except Exception:
        messages.error(request, "No admission record found.")
        return redirect("student_dashboard")
    if app.status not in ("admitted",):
        messages.warning(request, "Invoice not available at this stage.")
        return redirect("student_dashboard")
    invoice, _ = SchoolFeeInvoice.objects.get_or_create(
        application=app, defaults={"session": app.session, "amount": 25000})
    if request.method == "POST" and invoice.status == "generated":
        ref  = request.POST.get("payment_reference","").strip()
        bank = request.POST.get("payment_bank","").strip()
        date = request.POST.get("payment_date","").strip()
        if ref and bank and date:
            invoice.payment_reference = ref
            invoice.payment_bank      = bank
            invoice.payment_date      = date
            invoice.status            = "submitted"
            invoice.save()
            app.status = "school_fee_submitted"
            app.save()
            messages.success(request, "Payment submitted. Await registrar approval.")
            return redirect("student_dashboard")
        messages.error(request, "Fill all payment fields.")
    return render(request, "admissions/student/invoice.html",
                  {"invoice": invoice, "app": app, "banks": BANKS})

@login_required
def invoice_pdf(request):
    try:
        invoice = request.user.student.application.school_fee
        app     = invoice.application
    except Exception:
        return redirect("student_dashboard")
    from documents.views import render_pdf
    fname = "SchoolFee_" + invoice.invoice_number.replace("/","_") + ".pdf"
    return render_pdf("admissions/student/invoice_pdf.html", {"invoice": invoice, "app": app}, fname)

@login_required
def registrar_list(request):
    status_filter = request.GET.get("status","")
    apps = Application.objects.select_related("programme","session").order_by("-created_at")
    if status_filter:
        apps = apps.filter(status=status_filter)
    counts = {
        "all":                  Application.objects.count(),
        "app_fee_submitted":    Application.objects.filter(status="app_fee_submitted").count(),
        "admitted":             Application.objects.filter(status="admitted").count(),
        "school_fee_submitted": Application.objects.filter(status="school_fee_submitted").count(),
        "school_fee_approved":  Application.objects.filter(status="school_fee_approved").count(),
        "rejected":             Application.objects.filter(status="rejected").count(),
    }
    return render(request, "admissions/registrar/list.html",
                  {"apps": apps, "counts": counts, "status_filter": status_filter})

@login_required
def registrar_detail(request, pk):
    app = get_object_or_404(Application, pk=pk)
    return render(request, "admissions/registrar/detail.html", {
        "app": app,
        "olevel": getattr(app, "olevel", None),
        "invoice": getattr(app, "school_fee", None),
    })

@login_required
def confirm_app_fee(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if request.method == "POST":
        app.app_fee_confirmed    = True
        app.app_fee_confirmed_by = request.user
        app.status               = "app_fee_confirmed"
        app.save()
        messages.success(request, f"App fee confirmed for {app.get_full_name()}")
    return redirect("admissions:registrar_detail", pk=pk)

@login_required
def admit(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if request.method == "POST":
        if not app.app_fee_confirmed:
            messages.error(request, "Confirm application fee first.")
            return redirect("admissions:registrar_detail", pk=pk)
        if app.status in ("admitted","school_fee_submitted","school_fee_approved"):
            messages.warning(request, "Already admitted.")
            return redirect("admissions:registrar_detail", pk=pk)
        try:
            from .utils import admit_applicant
            admit_applicant(app, request.user)
            messages.success(request, f"Admitted! Login: {app.application_number}")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect("admissions:registrar_detail", pk=pk)

@login_required
def reject(request, pk):
    app = get_object_or_404(Application, pk=pk)
    if request.method == "POST":
        app.status           = "rejected"
        app.rejection_reason = request.POST.get("reason","")
        app.save()
        messages.success(request, f"{app.get_full_name()} rejected.")
    return redirect("admissions:registrar_detail", pk=pk)

def admission_letter(request, pk):
    app = get_object_or_404(Application, pk=pk)
    from documents.views import render_pdf
    fname = "Admission_" + app.application_number.replace("/","_") + ".pdf"
    return render_pdf("admissions/letter_pdf.html", {"app": app}, fname)

@login_required
def registrar_school_fees(request):
    status_filter = request.GET.get("status","")
    invoices = SchoolFeeInvoice.objects.select_related(
        "application__programme","application__session").order_by("-created_at")
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    return render(request, "admissions/registrar/school_fees.html", {
        "invoices": invoices,
        "status_filter": status_filter,
        "pending_count": SchoolFeeInvoice.objects.filter(status="submitted").count(),
    })

@login_required
def approve_school_fee(request, pk):
    invoice = get_object_or_404(SchoolFeeInvoice, pk=pk)
    if request.method == "POST":
        try:
            from .utils import assign_matric
            matric = assign_matric(invoice, request.user)
            messages.success(request, f"Matric assigned: {matric} to {invoice.application.get_full_name()}")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect("admissions:registrar_school_fees")

@login_required
def reject_school_fee(request, pk):
    invoice = get_object_or_404(SchoolFeeInvoice, pk=pk)
    if request.method == "POST":
        invoice.status             = "rejected"
        invoice.save()
        invoice.application.status = "admitted"
        invoice.application.save()
        messages.warning(request, "School fee rejected.")
    return redirect("admissions:registrar_school_fees")
