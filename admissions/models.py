from django.db import models
from django.conf import settings

GRADE_CHOICES = [("A1","A1"),("B2","B2"),("B3","B3"),("C4","C4"),("C5","C5"),("C6","C6"),("D7","D7"),("E8","E8"),("F9","F9")]
STATUS_CHOICES = [
    ("pending","Pending App Fee Payment"),
    ("app_fee_submitted","App Fee Submitted"),
    ("app_fee_confirmed","App Fee Confirmed"),
    ("admitted","Admitted - Awaiting School Fee"),
    ("school_fee_submitted","School Fee Submitted"),
    ("school_fee_approved","School Fee Approved - Matric Assigned"),
    ("rejected","Rejected"),
]
EXAM_TYPES = [("WAEC","WAEC"),("NECO","NECO"),("NABTEB","NABTEB")]
SUBJECTS = [
    ("english","English Language"),("mathematics","Mathematics"),
    ("biology","Biology"),("chemistry","Chemistry"),("physics","Physics"),
    ("agriculture","Agriculture"),("economics","Economics"),
    ("commerce","Commerce"),("accounting","Accounting"),
    ("government","Government"),("history","History"),
    ("geography","Geography"),("civic_education","Civic Education"),
    ("literature","Literature in English"),("hausa","Hausa Language"),
    ("yoruba","Yoruba Language"),("igbo","Igbo Language"),
    ("french","French"),("computer","Computer Studies"),
    ("islamic_studies","Islamic Studies"),
    ("christian_rel","Christian Religious Studies"),
    ("further_maths","Further Mathematics"),
    ("data_processing","Data Processing"),
    ("home_economics","Home Economics"),("other","Other"),
]

def application_photo_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1]
    return f"admissions/photos/{instance.application_number}{ext}"

class Application(models.Model):
    GENDER = [("M","Male"),("F","Female")]
    application_number   = models.CharField(max_length=30, unique=True, blank=True)
    status               = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)
    first_name           = models.CharField(max_length=100)
    last_name            = models.CharField(max_length=100)
    middle_name          = models.CharField(max_length=100, blank=True)
    date_of_birth        = models.DateField()
    gender               = models.CharField(max_length=1, choices=GENDER)
    nationality          = models.CharField(max_length=80, default="Nigerian")
    state_of_origin      = models.CharField(max_length=80)
    lga                  = models.CharField(max_length=80)
    religion             = models.CharField(max_length=50, blank=True)
    photo                = models.ImageField(upload_to=application_photo_path, blank=True, null=True)
    phone                = models.CharField(max_length=20)
    email                = models.EmailField()
    address              = models.TextField()
    programme            = models.ForeignKey("academics.Programme", on_delete=models.SET_NULL, null=True)
    session              = models.ForeignKey("core.Session", on_delete=models.SET_NULL, null=True)
    app_fee_reference    = models.CharField(max_length=100, blank=True)
    app_fee_date         = models.DateField(null=True, blank=True)
    app_fee_bank         = models.CharField(max_length=100, blank=True)
    app_fee_confirmed    = models.BooleanField(default=False)
    app_fee_confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_app_fees")
    admitted_by          = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="admitted_applications")
    admission_date       = models.DateTimeField(null=True, blank=True)
    matric_number        = models.CharField(max_length=30, blank=True)
    rejection_reason     = models.TextField(blank=True)
    student              = models.OneToOneField("students.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="application")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application_number} - {self.get_full_name()}"

    def get_full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    def save(self, *args, **kwargs):
        if not self.application_number:
            import datetime
            year = datetime.date.today().year
            count = Application.objects.filter(created_at__year=year).count() + 1
            self.application_number = f"CMT/APP/{year}/{count:04d}"
        super().save(*args, **kwargs)

    @property
    def has_matric(self):
        return bool(self.matric_number)

class OLevelResult(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="olevel")
    exam_type   = models.CharField(max_length=10, choices=EXAM_TYPES)
    exam_year   = models.CharField(max_length=4)
    exam_number = models.CharField(max_length=30)
    sitting     = models.CharField(max_length=10, choices=[("1st","1st Sitting"),("2nd","2nd Sitting")], default="1st")

class OLevelSubject(models.Model):
    result  = models.ForeignKey(OLevelResult, on_delete=models.CASCADE, related_name="subjects")
    subject = models.CharField(max_length=50, choices=SUBJECTS)
    grade   = models.CharField(max_length=2, choices=GRADE_CHOICES)
    class Meta:
        unique_together = ["result","subject"]
    def __str__(self):
        return f"{self.get_subject_display()} - {self.grade}"

class SchoolFeeInvoice(models.Model):
    STATUS = [("generated","Invoice Generated"),("submitted","Payment Submitted"),("approved","Approved - Matric Assigned"),("rejected","Rejected")]
    application       = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="school_fee")
    invoice_number    = models.CharField(max_length=30, unique=True, blank=True)
    session           = models.ForeignKey("core.Session", on_delete=models.SET_NULL, null=True)
    amount            = models.DecimalField(max_digits=10, decimal_places=2, default=25000)
    status            = models.CharField(max_length=20, choices=STATUS, default="generated")
    created_at        = models.DateTimeField(auto_now_add=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_bank      = models.CharField(max_length=100, blank=True)
    payment_date      = models.DateField(null=True, blank=True)
    approved_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_school_fees")
    approved_at       = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import datetime
            yr = datetime.date.today().year
            count = SchoolFeeInvoice.objects.count() + 1
            self.invoice_number = f"INV/SF/{yr}/{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.application.get_full_name()}"
