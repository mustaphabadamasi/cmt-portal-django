from django.db import models
from django.conf import settings
from decimal import Decimal

STATUS = [
    ('draft',     'Draft'),
    ('submitted', 'Submitted to Registrar'),
    ('approved',  'Approved'),
    ('rejected',  'Rejected'),
]

def compute_grade(total):
    t = float(total)
    if t >= 70: return 'A', Decimal('5.0')
    elif t >= 60: return 'B', Decimal('4.0')
    elif t >= 50: return 'C', Decimal('3.0')
    elif t >= 45: return 'D', Decimal('2.0')
    elif t >= 40: return 'E', Decimal('1.0')
    else:         return 'F', Decimal('0.0')


class CourseResult(models.Model):
    student     = models.ForeignKey('students.Student',  on_delete=models.CASCADE, related_name='course_results')
    course      = models.ForeignKey('academics.Course',  on_delete=models.CASCADE)
    semester    = models.ForeignKey('core.Semester',     on_delete=models.CASCADE)
    session     = models.ForeignKey('core.Session',      on_delete=models.CASCADE)

    ca_score    = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Max 40')
    exam_score  = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Max 60')
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade       = models.CharField(max_length=2, blank=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    status      = models.CharField(max_length=20, choices=STATUS, default='draft')
    entered_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, related_name='entered_results')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='approved_results')
    entered_at  = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    remark      = models.TextField(blank=True)

    class Meta:
        unique_together = ['student','course','semester']
        ordering = ['student__reg_number']

    def __str__(self):
        return f"{self.student.reg_number} | {self.course.code} | {self.grade}"

    def save(self, *args, **kwargs):
        if self.ca_score is not None and self.exam_score is not None:
            self.total_score = self.ca_score + self.exam_score
            self.grade, self.grade_point = compute_grade(self.total_score)
        super().save(*args, **kwargs)

    @property
    def remark_text(self):
        r = {'A':'Excellent','B':'Good','C':'Credit','D':'Pass','E':'Pass','F':'Fail'}
        return r.get(self.grade, '-')


class ResultBatch(models.Model):
    """Tracks lecturer submission of a full course result for registrar approval."""
    lecturer    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                    related_name='result_batches')
    course      = models.ForeignKey('academics.Course',  on_delete=models.CASCADE)
    semester    = models.ForeignKey('core.Semester',     on_delete=models.CASCADE)
    session     = models.ForeignKey('core.Session',      on_delete=models.CASCADE)
    status      = models.CharField(max_length=20, choices=STATUS, default='draft')
    submitted_at= models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='approved_batches')
    approved_at = models.DateTimeField(null=True, blank=True)
    reject_reason      = models.TextField(blank=True)
    senate_published   = models.BooleanField(default=False)
    senate_published_at= models.DateTimeField(null=True, blank=True)
    senate_published_by= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='senate_published_batches')

    class Meta:
        unique_together = ['lecturer','course','semester']

    def __str__(self):
        return f"{self.course.code} | {self.semester} | {self.status}"

    @property
    def student_count(self):
        return CourseResult.objects.filter(
            course=self.course, semester=self.semester).count()

    @property
    def entered_count(self):
        return CourseResult.objects.filter(
            course=self.course, semester=self.semester,
            total_score__isnull=False).count()