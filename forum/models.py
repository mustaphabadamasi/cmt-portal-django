from django.db import models
from django.conf import settings


class ForumPost(models.Model):
    course     = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='forum_posts')
    semester   = models.ForeignKey('core.Semester',    on_delete=models.CASCADE, related_name='forum_posts')
    author     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_posts')
    title      = models.CharField(max_length=300)
    content    = models.TextField()
    attachment = models.FileField(upload_to='forum/attachments/', blank=True, null=True)
    is_pinned  = models.BooleanField(default=False)
    likes      = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='liked_posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.course.code} — {self.title}"

    @property
    def reply_count(self):
        return self.replies.count()

    @property
    def like_count(self):
        return self.likes.count()


class ForumReply(models.Model):
    post       = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='replies')
    author     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forum_replies')
    content    = models.TextField()
    attachment = models.FileField(upload_to='forum/attachments/', blank=True, null=True)
    likes      = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='liked_replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author.get_full_name()} on {self.post.title}"

    @property
    def like_count(self):
        return self.likes.count()
