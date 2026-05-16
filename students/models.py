from django.db import models
from accounts.models import User
from academics.models import Programme
from core.models import Session, Semester


def photo_upload_path(instance, filename):
    return f'students/{instance.reg_number}/{filename}'


class Student(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('graduated', 'Graduated'),
        ('withdrawn', 'Withdrawn'),
        ('suspended', 'Suspended'),
    ]
    
    user             = models.OneToOneField(User, on_delete=models.CASCADE)
    reg_number       = models.CharField(max_length=30, unique=True)
    programme        = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True)
    current_session  = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True)
    current_semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True)
    photo            = models.ImageField(upload_to=photo_upload_path, blank=True, null=True)

    GENDER_CHOICES = [("M", "MALE"), ("F", "FEMALE")]
    gender          = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, default="M")
    date_of_birth   = models.DateField(null=True, blank=True)
    state_of_origin = models.CharField(max_length=50, blank=True, default="KATSINA")
    entry_mode      = models.CharField(max_length=20, blank=True, default="O-LEVEL")
    year_admitted   = models.CharField(max_length=9, blank=True, default="")

    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    date_enrolled    = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-date_enrolled']  # Optional: newer students first

    def __str__(self):
        return f"{self.reg_number} - {self.user.get_full_name()}"

    @property
    def level(self):
        reg = str(self.reg_number or "")
        if "/24/" in reg:
            return "Diploma II"
        elif "/25/" in reg:
            return "Diploma I"
        return "Diploma I"


# ✅ Fixed: Moved outside Student class (proper indentation)
class CourseRegistration(models.Model):
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE,
        related_name='registrations'  # Access via: student.registrations.all()
    )
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    courses = models.ManyToManyField('academics.Course', through='CourseRegistrationDetail')
    date_registered = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'semester')
        verbose_name = 'Course Registration'
        verbose_name_plural = 'Course Registrations'

    def __str__(self):
        return f"{self.student.reg_number} - {self.semester}"

    @property
    def total_courses(self):
        return self.courses.count()


# ✅ Recommended: Through model for M2M relationship
class CourseRegistrationDetail(models.Model):
    registration = models.ForeignKey(CourseRegistration, on_delete=models.CASCADE)
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE)
    # Add more fields as needed:
    # - score (for storing grades)
    # - is_retake (boolean)
    # - date_added
    
    class Meta:
        unique_together = ('registration', 'course')
        verbose_name = 'Registered Course'
        verbose_name_plural = 'Registered Courses'

    def __str__(self):
        return f"{self.registration.student} - {self.course}"