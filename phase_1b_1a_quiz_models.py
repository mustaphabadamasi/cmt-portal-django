#!/usr/bin/env python3
"""
Phase 1B.1a — Quiz data model (MCQ).
Appends Quiz / Question / Choice to lecturers/models.py. Idempotent.
"""
import pathlib, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

MODEL_ADDITION = '''

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
'''

models_path = ROOT / 'lecturers/models.py'
content = models_path.read_text(encoding='utf-8')
if 'class Quiz(' in content:
    print('• Quiz models already present in lecturers/models.py, skipping')
else:
    models_path.write_text(content.rstrip() + '\n' + MODEL_ADDITION + '\n', encoding='utf-8')
    print('✓ appended Quiz, Question, Choice models to lecturers/models.py')

print()
print('Now run:')
print('  python manage.py makemigrations lecturers')
print('  python manage.py migrate')
print('  python manage.py check')