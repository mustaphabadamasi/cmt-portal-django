
from django.db import models
from django.conf import settings
 
 
class Session(models.Model):
    name        = models.CharField(max_length=20, unique=True)  # e.g. 2025/2026
    is_active   = models.BooleanField(default=False)
    start_date  = models.DateField(null=True, blank=True)
    end_date    = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-name']
 
    def __str__(self):
        return self.name
 
    def save(self, *args, **kwargs):
        # Only one session can be active at a time
        if self.is_active:
            Session.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
 
 
class Semester(models.Model):
    SEMESTER_CHOICES = [
        ('First Semester',  'First Semester'),
        ('Second Semester', 'Second Semester'),
    ]
    session    = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='semesters')
    name       = models.CharField(max_length=20, choices=SEMESTER_CHOICES)
    is_active  = models.BooleanField(default=False)
    reg_open   = models.BooleanField(default=False, verbose_name='Course Registration Open')
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
 
    class Meta:
        unique_together = ['session', 'name']
        ordering = ['session', 'name']
 
    def __str__(self):
        return f"{self.session} - {self.name}"
 
    def save(self, *args, **kwargs):
        if self.is_active:
            Semester.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
