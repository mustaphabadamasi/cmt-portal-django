from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('bursar', 'Bursar'),
        ('academic_officer', 'Academic Secretary'),    # was 'Academic Officer'
        ('registrar', 'Registrar'),
        ('lecturer', 'Lecturer'),
        ('student', 'Student'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    must_change_password = models.BooleanField(default=False)

    def is_admin(self): return self.role == 'admin'
    def is_bursar(self): return self.role == 'bursar'
    def is_academic_officer(self): return self.role == 'academic_officer'
    def is_registrar(self): return self.role == 'registrar'
    def is_lecturer(self): return self.role == 'lecturer'
    def is_student(self): return self.role == 'student'