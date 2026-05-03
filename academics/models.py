from django.db import models

# Create your models here.
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self): return self.name

class Programme(models.Model):
    LEVEL_CHOICES = [('diploma1', 'Diploma I'), ('diploma2', 'Diploma II')]
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    def __str__(self): return f"{self.name} ({self.get_level_display()})"

class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=15)
    unit = models.PositiveIntegerField(default=2)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE)
    semester_number = models.PositiveIntegerField(choices=[(1,'1'),(2,'2'),(3,'3'),(4,'4')])

    def __str__(self): return f"{self.code} - {self.title}"