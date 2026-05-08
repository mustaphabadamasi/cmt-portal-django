from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self): return self.name


class Programme(models.Model):
    LEVEL_CHOICES = [('diploma1', 'Diploma I'), ('diploma2', 'Diploma II')]
    name       = models.CharField(max_length=100)
    code       = models.CharField(max_length=10)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level      = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    def __str__(self): return f"{self.name} ({self.get_level_display()})"


class Course(models.Model):
    title           = models.CharField(max_length=200)
    code            = models.CharField(max_length=15)
    unit            = models.PositiveIntegerField(default=2)
    programme       = models.ForeignKey(Programme, on_delete=models.CASCADE)
    semester_number = models.PositiveIntegerField(choices=[(1,'1'),(2,'2'),(3,'3'),(4,'4')])

    def __str__(self): return f"{self.code} - {self.title}"


class SemesterCourseStructure(models.Model):
    LEVEL_CHOICES = [('diploma1', 'Diploma I'), ('diploma2', 'Diploma II')]
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='course_structures')
    level     = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    semester  = models.ForeignKey('core.Semester', on_delete=models.CASCADE, related_name='course_structures')
    courses   = models.ManyToManyField(Course, blank=True, related_name='structures')

    class Meta:
        unique_together = ['programme', 'level', 'semester']

    def __str__(self):
        return f"{self.programme} | {self.level} | {self.semester}"


class CourseRegistration(models.Model):
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('carryover',  'Carry Over'),
        ('completed',  'Completed'),
        ('failed',     'Failed'),
    ]
    student       = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='course_registrations')
    semester      = models.ForeignKey('core.Semester', on_delete=models.CASCADE, related_name='course_registrations')
    course        = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registrations')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    score         = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade         = models.CharField(max_length=2, blank=True)
    is_carryover  = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'semester', 'course']

    def __str__(self):
        return f"{self.student} - {self.course.code} ({self.semester})"


class CourseOutline(models.Model):
    name       = models.CharField(max_length=200)
    programme  = models.ForeignKey('Programme', on_delete=models.CASCADE, related_name='outlines')
    level      = models.CharField(max_length=20, choices=[('Diploma I','Diploma I'),('Diploma II','Diploma II')])
    semester   = models.ForeignKey('core.Semester', on_delete=models.CASCADE, related_name='outlines')
    courses    = models.ManyToManyField('Course', blank=True)
    min_units  = models.PositiveIntegerField(default=15)
    max_units  = models.PositiveIntegerField(default=24)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['programme', 'level', 'semester']
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def total_units(self):
        return sum(c.unit for c in self.courses.all())
