from django.contrib import admin
from .models import LiveClass, ClassAttendance

class AttendanceInline(admin.TabularInline):
    model = ClassAttendance
    extra = 0
    readonly_fields = ('student', 'joined_at', 'left_at')

@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display  = ('title', 'course', 'lecturer', 'status', 'scheduled_start', 'attendance_count')
    list_filter   = ('status', 'course', 'semester')
    inlines       = [AttendanceInline]

@admin.register(ClassAttendance)
class ClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'live_class', 'joined_at', 'left_at')
