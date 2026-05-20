from django.contrib import admin
from .models import CourseResult, ResultBatch

@admin.register(CourseResult)
class CourseResultAdmin(admin.ModelAdmin):
    list_display  = ('student','course','semester','ca_score','exam_score','total_score','grade','status')
    list_filter   = ('status','semester','grade')
    search_fields = ('student__reg_number','course__code')

@admin.register(ResultBatch)
class ResultBatchAdmin(admin.ModelAdmin):
    list_display = ('course','semester','lecturer','status','submitted_at')
    list_filter  = ('status','semester')