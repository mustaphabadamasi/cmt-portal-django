from django.contrib import admin
from .models import Lecturer, LecturerCourse


class LecturerCourseInline(admin.TabularInline):
    model = LecturerCourse
    fk_name = 'lecturer'
    extra = 1
    fields = ['course', 'semester', 'is_active', 'notes']


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display  = ['staff_id', 'name', 'department', 'phone', 'status', 'courses_count']
    list_filter   = ['status', 'gender', 'department']
    search_fields = ['staff_id', 'user__first_name', 'user__last_name',
                     'user__username', 'user__email']
    inlines       = [LecturerCourseInline]

    def name(self, obj):
        return obj.full_name
    name.short_description = 'Name'

    def courses_count(self, obj):
        return obj.active_courses_count
    courses_count.short_description = '# Active Courses'


@admin.register(LecturerCourse)
class LecturerCourseAdmin(admin.ModelAdmin):
    list_display  = ['lecturer', 'course', 'semester', 'is_active', 'assigned_at']
    list_filter   = ['is_active', 'semester']
    search_fields = ['lecturer__staff_id',
                     'lecturer__user__first_name', 'lecturer__user__last_name',
                     'course__code', 'course__title']