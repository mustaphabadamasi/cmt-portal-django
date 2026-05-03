from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Department, Programme, Course

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']

@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'level']
    list_filter = ['department', 'level']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'programme', 'semester_number', 'unit']
    list_filter = ['programme', 'semester_number']