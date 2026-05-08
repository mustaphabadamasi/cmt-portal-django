from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('bursar', 'Bursar'),
    ('academic_officer', 'Academic Officer'),
    ('registrar', 'Registrar'),
    ('student', 'Student'),
]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    def is_admin(self): return self.role == 'admin'
    def is_bursar(self): return self.role == 'bursar'
    def is_student(self): return self.role == 'student'
    must_change_password = models.BooleanField(default=False)