from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator




class MatricUsernameValidator(UnicodeUsernameValidator):
    """Allow forward-slash so full matric numbers like DPL/PAD/24/152 can be usernames"""
    regex = r'^[a-zA-Z0-9_./@+-]+$'
    message = 'Enter a valid username.'


class User(AbstractUser):
    username_validator = MatricUsernameValidator()
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={'unique': 'A user with that username already exists.'},
    )

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