from django.db import models
import uuid


def generate_room_name(course_code):
    short_uuid = str(uuid.uuid4()).replace('-', '')[:10]
    clean_code = ''.join(c for c in course_code.lower() if c.isalnum())
    return f"cmt-{clean_code}-{short_uuid}"


class LiveClass(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live',      'Live'),
        ('ended',     'Ended'),
        ('cancelled', 'Cancelled'),
    ]

    title           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    course          = models.ForeignKey('academics.Course',   on_delete=models.CASCADE, related_name='live_classes')
    semester        = models.ForeignKey('core.Semester',      on_delete=models.CASCADE, related_name='live_classes')
    lecturer        = models.ForeignKey('lecturers.Lecturer', on_delete=models.CASCADE, related_name='live_classes')
    scheduled_start = models.DateTimeField()
    scheduled_end   = models.DateTimeField()
    jitsi_room_name = models.CharField(max_length=200, unique=True, blank=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    actual_start    = models.DateTimeField(null=True, blank=True)
    actual_end      = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_start']

    def __str__(self):
        return f"{self.course.code} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.jitsi_room_name:
            self.jitsi_room_name = generate_room_name(self.course.code)
        super().save(*args, **kwargs)

    @property
    def jitsi_url(self):
        return f"https://meet.jit.si/{self.jitsi_room_name}"

    @property
    def is_live(self):
        return self.status == 'live'

    @property
    def attendance_count(self):
        return self.attendance.count()


class ClassAttendance(models.Model):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='attendance')
    student    = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='class_attendance')
    joined_at  = models.DateTimeField(auto_now_add=True)
    left_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['live_class', 'student']

    def __str__(self):
        return f"{self.student.reg_number} → {self.live_class.title}"

    @property
    def duration_minutes(self):
        if self.left_at:
            return int((self.left_at - self.joined_at).total_seconds() / 60)
        return None
