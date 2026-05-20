from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('recipient', 'type', 'title', 'is_read', 'created_at')
    list_filter   = ('type', 'is_read')
    actions       = ['mark_read']

    def mark_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_read.short_description = 'Mark selected as read'
