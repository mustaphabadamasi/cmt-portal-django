from django.contrib import admin
from .models import ForumPost, ForumReply

class ReplyInline(admin.TabularInline):
    model  = ForumReply
    extra  = 0
    fields = ('author', 'content', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display  = ('title', 'course', 'author', 'is_pinned', 'like_count', 'reply_count', 'created_at')
    list_filter   = ('is_pinned', 'course')
    inlines       = [ReplyInline]

@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
