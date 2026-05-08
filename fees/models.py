from django.db import models
from django.conf import settings
from students.models import Student
from core.models import Session, Semester


class FeePayment(models.Model):
    PAYMENT_TYPE = [('session', 'Full Session'), ('semester', 'Per Semester')]
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    student        = models.ForeignKey(Student, on_delete=models.CASCADE)
    session        = models.ForeignKey(Session, on_delete=models.CASCADE)
    semester       = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type   = models.CharField(max_length=10, choices=PAYMENT_TYPE)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    date_requested = models.DateTimeField(auto_now_add=True)
    date_approved  = models.DateTimeField(null=True, blank=True)
    approved_by    = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.amount:
            self.amount = 50000 if self.payment_type == 'session' else 25000
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.payment_type} - {self.status}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    TYPE_CHOICES = [
        ('school_fees',  'School Fees'),
        ('acceptance',   'Acceptance Fee'),
        ('development',  'Development Levy'),
        ('exam',         'Exam Fee'),
        ('other',        'Other'),
    ]
    student      = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    session      = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True)
    semester     = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True)
    payment_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='school_fees')
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    reference    = models.CharField(max_length=50, unique=True)
    receipt_no   = models.CharField(max_length=30, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    evidence     = models.ImageField(upload_to='payment_evidence/', null=True, blank=True)
    note         = models.TextField(blank=True)
    approved_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='approved_payments')
    approved_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} - {self.payment_type} - {self.status}"
