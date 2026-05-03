from django.db import models

# Create your models here.
from django.db import models

class Session(models.Model):
    name = models.CharField(max_length=20)  # e.g. 2024/2025
    is_active = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self): return self.name

class Semester(models.Model):
    SEMESTER_CHOICES = [('first', 'First'), ('second', 'Second')]
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    is_active = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self): return f"{self.session} - {self.get_name_display()} Semester"