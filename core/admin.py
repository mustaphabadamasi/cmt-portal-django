from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Session, Semester

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active']
    list_editable = ['is_active']

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_active', 'start_date', 'end_date']
    list_editable = ['is_active']
    list_filter = ['session']