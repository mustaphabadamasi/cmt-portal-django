from django.conf import settings
from django.db import models


class Lecturer(models.Model):
    TITLE_CHOICES = [
        ('Mr.', 'Mr.'), ('Mrs.', 'Mrs.'), ('Miss', 'Miss'),
        ('Dr.', 'Dr.'), ('Prof.', 'Prof.'), ('Engr.', 'Engr.'),
        ('Mallam', 'Mallam'), ('Hajiya', 'Hajiya'), ('Alh.', 'Alh.'),
    ]
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('retired', 'Retired'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lecturer_profile',
    )
    staff_id      = models.CharField(max_length=30, unique=True)
    title         = models.CharField(max_length=15, choices=TITLE_CHOICES, blank=True)
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    department    = models.CharField(max_length=120, blank=True)
    photo         = models.ImageField(upload_to='lecturers/photos/', blank=True, null=True)
    date_employed = models.DateField(null=True, blank=True)
    status        = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        full = self.user.get_full_name() or self.user.username
        prefix = f"{self.title} " if self.title else ""
        return f"{prefix}{full}".strip()

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def active_courses_count(self):
        return self.course_assignments.filter(is_active=True).count()


class LecturerCourse(models.Model):
    """Assignment of a lecturer to a course for a given semester."""

    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE,
        related_name='course_assignments',
    )
    course = models.ForeignKey(
        'academics.Course',
        on_delete=models.CASCADE,
        related_name='lecturer_assignments',
    )
    semester = models.ForeignKey(
        'core.Semester',
        on_delete=models.CASCADE,
        related_name='lecturer_assignments',
    )
    is_active   = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lecturer_assignments_made',
    )

    class Meta:
        unique_together = [('lecturer', 'course', 'semester')]
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.lecturer} -> {self.course} ({self.semester})"


# ============================================================
# Phase 1B — Quiz module (MCQ, contributes to 20-mark CA bucket)
# ============================================================

class Quiz(models.Model):
    """A multiple-choice quiz created by a lecturer for one of their assigned courses."""

    course     = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='quizzes')
    semester   = models.ForeignKey('core.Semester',    on_delete=models.CASCADE, related_name='quizzes')
    created_by = models.ForeignKey(Lecturer,           on_delete=models.CASCADE, related_name='quizzes_created')

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Instructions shown to students before they start.")

    max_score          = models.PositiveIntegerField(default=20, help_text="Total marks this quiz contributes (20-mark CA bucket).")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Optional. Blank = no time limit.")

    available_from  = models.DateTimeField(help_text="Students can begin attempting from this time.")
    available_until = models.DateTimeField(help_text="Attempts blocked after this time. Scores revealed only after.")

    questions_to_attempt = models.PositiveIntegerField(null=True, blank=True, help_text="If set, each student sees this many random questions from the bank. Blank = show all.")

    is_published = models.BooleanField(default=False, help_text="Unpublished quizzes are invisible to students.")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course.code} - {self.title}"

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        return sum(q.points for q in self.questions.all()) or 0

    @property
    def status(self):
        """One of: draft, upcoming, open, closed."""
        from django.utils import timezone
        if not self.is_published:
            return 'draft'
        now = timezone.now()
        if now < self.available_from:
            return 'upcoming'
        if now > self.available_until:
            return 'closed'
        return 'open'


class Question(models.Model):
    """A single question within a quiz."""

    quiz   = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text   = models.TextField()
    points = models.PositiveIntegerField(default=1, help_text="Marks awarded for getting this right.")
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]

    @property
    def correct_choice(self):
        return self.choices.filter(is_correct=True).first()

    @property
    def is_ready(self):
        """Question is ready if it has >=2 choices and exactly one is marked correct."""
        choices = self.choices.all()
        return choices.count() >= 2 and choices.filter(is_correct=True).count() == 1


class Choice(models.Model):
    """One option of a multiple-choice question."""

    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text       = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:80]

# ============================================================
# Phase 1B.2 — Quiz attempts (student-side)
# ============================================================

class QuizAttempt(models.Model):
    """One student's attempt at a quiz. Max one per (student, quiz)."""

    quiz    = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='quiz_attempts')

    started_at     = models.DateTimeField(auto_now_add=True)
    submitted_at   = models.DateTimeField(null=True, blank=True)
    is_submitted   = models.BooleanField(default=False)
    auto_submitted = models.BooleanField(default=False)

    score     = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_score = models.PositiveIntegerField()

    class Meta:
        unique_together = [('quiz', 'student')]
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.reg_number} - {self.quiz.title}"

    @property
    def question_count(self):
        return self.answers.count()

    @property
    def correct_count(self):
        return sum(1 for a in self.answers.all() if a.selected_choice_id and a.selected_choice.is_correct)


class AttemptAnswer(models.Model):
    """One row per question presented to a student in their attempt."""

    attempt         = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question        = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    order           = models.PositiveIntegerField()

    class Meta:
        unique_together = [('attempt', 'question')]
        ordering = ['order']

    @property
    def is_correct(self):
        return bool(self.selected_choice_id and self.selected_choice.is_correct)



# ============ ASSIGNMENT MODELS (Phase 1C) ============

class Assignment(models.Model):
    """One assignment per course = 20 marks (10 individual + 10 group)"""
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='assignments')
    semester = models.ForeignKey('core.Semester', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(help_text='Assignment instructions for both individual and group parts')
    
    individual_deadline = models.DateTimeField()
    group_deadline = models.DateTimeField()
    
    max_individual_mark = models.PositiveIntegerField(default=10)
    max_group_mark = models.PositiveIntegerField(default=10)
    
    created_by = models.ForeignKey('lecturers.Lecturer', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.course.code} - {self.title}'
    
    class Meta:
        ordering = ['-created_at']


class AssignmentGroup(models.Model):
    """Groups for the group portion of an assignment"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=50, help_text='e.g. Group A, Group B')
    leader = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='led_groups')
    members = models.ManyToManyField('students.Student', related_name='assignment_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.assignment.title} - {self.name}'
    
    class Meta:
        unique_together = [['assignment', 'name']]
        ordering = ['name']


class IndividualSubmission(models.Model):
    """One per student per assignment - 10 marks"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='individual_submissions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    
    content_text = models.TextField(blank=True, help_text='Text answer')
    content_file = models.FileField(upload_to='assignments/individual/%Y/%m/', blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(default=False)
    
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey('lecturers.Lecturer', on_delete=models.SET_NULL, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-flag as late
        if not self.pk and self.assignment.individual_deadline:
            from django.utils import timezone
            self.is_late = timezone.now() > self.assignment.individual_deadline
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.student.reg_number} - {self.assignment.title}'
    
    class Meta:
        unique_together = [['assignment', 'student']]


class GroupSubmission(models.Model):
    """One per group per assignment - 10 marks, only group leader can submit"""
    group = models.OneToOneField(AssignmentGroup, on_delete=models.CASCADE, related_name='submission')
    submitted_by = models.ForeignKey('students.Student', on_delete=models.CASCADE, help_text='Must be group leader')
    
    content_text = models.TextField(blank=True)
    content_file = models.FileField(upload_to='assignments/group/%Y/%m/', blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(default=False)
    
    score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey('lecturers.Lecturer', on_delete=models.SET_NULL, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and self.group.assignment.group_deadline:
            from django.utils import timezone
            self.is_late = timezone.now() > self.group.assignment.group_deadline
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.group} - submission'
