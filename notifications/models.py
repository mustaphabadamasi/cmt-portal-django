from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('assignment', 'Assignment'),
        ('quiz',       'Quiz'),
        ('live_class', 'Live Class'),
        ('forum_post', 'Forum Post'),
        ('forum_reply','Forum Reply'),
        ('deadline',   'Deadline'),
        ('result',     'Result'),
        ('general',    'General'),
    ]
    ICONS = {
        'assignment': '📋',
        'quiz':       '❓',
        'live_class': '🔴',
        'forum_post': '💬',
        'forum_reply':'🗨️',
        'deadline':   '⏰',
        'result':     '📊',
        'general':    '🔔',
    }

    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    title      = models.CharField(max_length=200)
    message    = models.TextField(blank=True)
    link       = models.CharField(max_length=500, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"

    @property
    def icon(self):
        return self.ICONS.get(self.type, '🔔')
