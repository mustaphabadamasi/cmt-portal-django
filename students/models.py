from django.db import models

# Create your models here.
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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reg_number = models.CharField(max_length=30, unique=True)
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True)
    current_session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True)
    current_semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True)
    photo = models.ImageField(upload_to=photo_upload_path, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    date_enrolled = models.DateField(auto_now_add=True)

    def __str__(self): return f"{self.reg_number} - {self.user.get_full_name()}"

class CourseRegistration(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    courses = models.ManyToManyField('academics.Course')
    date_registered = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'semester')