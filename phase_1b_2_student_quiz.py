#!/usr/bin/env python3
"""
Phase 1B.2 — Student-side quiz taking.
Adds QuizAttempt + AttemptAnswer models, 4 views, 4 templates, sidebar link. Idempotent.
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')


# ========== MODEL ADDITIONS ==========
MODELS_ADDITION = r'''

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
'''


# ========== VIEWS ADDITION ==========
VIEWS_ADDITION = r'''

# ============================================================
# Phase 1B.2 — Student-side quiz views
# ============================================================
import datetime as _dt
import random as _rnd
from django.utils import timezone as _tz
from .models import QuizAttempt, AttemptAnswer


def student_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        u = request.user
        if u.role == 'student' and hasattr(u, 'student'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("This area is for students only.")
    return wrapper


@student_required
def student_quiz_list(request):
    from academics.models import CourseRegistration
    student = request.user.student
    pairs = set(CourseRegistration.objects.filter(
        student=student, status__in=['registered', 'carryover']
    ).values_list('course_id', 'semester_id'))
    quizzes = (Quiz.objects.filter(is_published=True)
               .select_related('course', 'semester')
               .order_by('-available_from'))
    visible = [q for q in quizzes if (q.course_id, q.semester_id) in pairs]
    by_quiz = {a.quiz_id: a for a in QuizAttempt.objects.filter(student=student, quiz__in=visible)}
    items = [{'quiz': q, 'attempt': by_quiz.get(q.id)} for q in visible]
    return render(request, 'lecturers/student_quiz_list.html', {'items': items, 'student': student})


@student_required
def quiz_start(request, pk):
    if request.method != 'POST':
        return redirect('lecturers:student_quiz_list')
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    student = request.user.student
    from academics.models import CourseRegistration
    if not CourseRegistration.objects.filter(
        student=student, course=quiz.course, semester=quiz.semester,
        status__in=['registered', 'carryover']
    ).exists():
        return HttpResponseForbidden("You are not registered for this course.")
    now = _tz.now()
    if now < quiz.available_from:
        messages.error(request, "Quiz is not yet open.")
        return redirect('lecturers:student_quiz_list')
    if now > quiz.available_until:
        messages.error(request, "This quiz has closed.")
        return redirect('lecturers:student_quiz_list')
    existing = QuizAttempt.objects.filter(quiz=quiz, student=student).first()
    if existing:
        if existing.is_submitted:
            messages.info(request, "You've already submitted this quiz.")
            return redirect('lecturers:quiz_attempt_result', pk=existing.pk)
        return redirect('lecturers:quiz_take', pk=existing.pk)
    bank = list(quiz.questions.prefetch_related('choices').all())
    bank = [q for q in bank if q.is_ready]
    if not bank:
        messages.error(request, "This quiz has no ready questions. Contact your lecturer.")
        return redirect('lecturers:student_quiz_list')
    n = min(quiz.questions_to_attempt or len(bank), len(bank))
    selected = _rnd.sample(bank, n)
    _rnd.shuffle(selected)
    with _qtx.atomic():
        attempt = QuizAttempt.objects.create(quiz=quiz, student=student, max_score=quiz.max_score)
        for i, q in enumerate(selected, start=1):
            AttemptAnswer.objects.create(attempt=attempt, question=q, order=i)
    return redirect('lecturers:quiz_take', pk=attempt.pk)


@student_required
def quiz_take(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'student'),
        pk=pk, student=request.user.student,
    )
    if attempt.is_submitted:
        return redirect('lecturers:quiz_attempt_result', pk=attempt.pk)
    quiz = attempt.quiz
    now = _tz.now()
    deadline = None
    if quiz.time_limit_minutes:
        deadline = attempt.started_at + _dt.timedelta(minutes=quiz.time_limit_minutes)
    effective = min(deadline, quiz.available_until) if deadline else quiz.available_until
    if now > effective:
        return _finalize_attempt(request, attempt, auto=True)
    if request.method == 'POST':
        with _qtx.atomic():
            for a in attempt.answers.select_related('question').all():
                cid = request.POST.get(f'q_{a.question_id}')
                if cid:
                    try:
                        choice = Choice.objects.get(pk=int(cid), question=a.question)
                        a.selected_choice = choice
                        a.save(update_fields=['selected_choice'])
                    except (Choice.DoesNotExist, ValueError):
                        pass
        return _finalize_attempt(request, attempt, auto=False)
    rng = _rnd.Random(attempt.pk)
    items = []
    for a in attempt.answers.select_related('question').prefetch_related('question__choices').order_by('order'):
        choices = list(a.question.choices.all())
        rng.shuffle(choices)
        items.append({'answer': a, 'question': a.question, 'choices': choices})
    remaining = int((effective - now).total_seconds())
    return render(request, 'lecturers/take_quiz.html', {
        'attempt': attempt, 'quiz': quiz,
        'questions_data': items,
        'remaining_seconds': remaining,
        'has_time_limit': bool(deadline),
    })


def _finalize_attempt(request, attempt, auto=False):
    answers = list(attempt.answers.select_related('selected_choice').all())
    asked = len(answers)
    correct = sum(1 for a in answers if a.selected_choice_id and a.selected_choice.is_correct)
    score = round((correct / asked) * float(attempt.max_score), 2) if asked else 0
    attempt.score = score
    attempt.is_submitted = True
    attempt.auto_submitted = auto
    attempt.submitted_at = _tz.now()
    attempt.save(update_fields=['score', 'is_submitted', 'auto_submitted', 'submitted_at'])
    messages.success(request, "Your quiz has been submitted.")
    return redirect('lecturers:quiz_attempt_result', pk=attempt.pk)


@student_required
def quiz_attempt_result(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'quiz__course', 'quiz__semester'),
        pk=pk, student=request.user.student,
    )
    show_score = _tz.now() > attempt.quiz.available_until
    return render(request, 'lecturers/quiz_result.html', {
        'attempt': attempt, 'quiz': attempt.quiz, 'show_score': show_score,
    })
'''


# ========== URL ADDITIONS ==========
URL_LINES = """    path('student/quizzes/',                  views.student_quiz_list,    name='student_quiz_list'),
    path('student/quizzes/<int:pk>/start/',   views.quiz_start,           name='quiz_start'),
    path('attempts/<int:pk>/take/',           views.quiz_take,            name='quiz_take'),
    path('attempts/<int:pk>/result/',         views.quiz_attempt_result,  name='quiz_attempt_result'),
"""


# ========== TEMPLATES ==========
STUDENT_QUIZ_LIST = r'''{% extends "base.html" %}
{% block page_title %}Available Quizzes{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">Available Quizzes</div>
    <div class="page-sub">Quizzes for your registered courses · {{ items|length }} total</div>
  </div>
</div>

<style>
  .qrow{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
  .qrow .info{flex:1;min-width:260px}
  .qtitle{font-weight:700;color:#111;font-size:15px;margin-bottom:4px}
  .meta{font-size:12px;color:#6b7280}
  .badge{display:inline-block;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700;letter-spacing:.3px}
  .b-open{background:#d1fae5;color:#065f46}
  .b-submitted{background:#dbeafe;color:#1e40af}
  .b-closed{background:#fee2e2;color:#991b1b}
  .b-upcoming{background:#fef3c7;color:#92400e}
  .b-progress{background:#fde68a;color:#92400e}
  .btn{padding:9px 18px;border-radius:8px;border:none;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
  .btn-start{background:#1a5c38;color:#fff}
  .btn-view{background:#fff;color:#1a5c38;border:1px solid #bbf7d0}
  .btn-cont{background:#c8881a;color:#fff}
</style>

{% for item in items %}
  <div class="qrow">
    <div class="info">
      <div class="qtitle">{{ item.quiz.title }}</div>
      <div class="meta">
        {{ item.quiz.course.code }} — {{ item.quiz.course.title }} · {{ item.quiz.semester }}
      </div>
      <div class="meta" style="margin-top:3px">
        {% if item.quiz.time_limit_minutes %}⏱ {{ item.quiz.time_limit_minutes }} min{% else %}⏱ No time limit{% endif %} ·
        {% if item.quiz.questions_to_attempt %}{{ item.quiz.questions_to_attempt }} random questions{% else %}{{ item.quiz.question_count }} question{{ item.quiz.question_count|pluralize }}{% endif %} ·
        {{ item.quiz.max_score }} marks
      </div>
      <div class="meta" style="margin-top:3px">
        Open: {{ item.quiz.available_from|date:"d M, H:i" }} → {{ item.quiz.available_until|date:"d M, H:i" }}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
      {% if item.attempt and item.attempt.is_submitted %}
        <span class="badge b-submitted">SUBMITTED</span>
        <a href="{% url 'lecturers:quiz_attempt_result' item.attempt.pk %}" class="btn btn-view">View Result</a>
      {% elif item.attempt %}
        <span class="badge b-progress">IN PROGRESS</span>
        <a href="{% url 'lecturers:quiz_take' item.attempt.pk %}" class="btn btn-cont">Continue</a>
      {% elif item.quiz.status == 'open' %}
        <span class="badge b-open">OPEN</span>
        <form method="post" action="{% url 'lecturers:quiz_start' item.quiz.pk %}" style="margin:0">
          {% csrf_token %}
          <button class="btn btn-start" type="submit">Start Quiz</button>
        </form>
      {% elif item.quiz.status == 'upcoming' %}
        <span class="badge b-upcoming">OPENS {{ item.quiz.available_from|date:"d M, H:i" }}</span>
      {% else %}
        <span class="badge b-closed">CLOSED</span>
      {% endif %}
    </div>
  </div>
{% empty %}
  <div style="text-align:center;color:#9ca3af;padding:48px;background:#fff;border:1px dashed #e5e7eb;border-radius:12px">
    <i class="bi bi-patch-question" style="font-size:48px;display:block;margin-bottom:10px"></i>
    No quizzes available right now.
  </div>
{% endfor %}
{% endblock %}
'''

TAKE_QUIZ = r'''{% extends "base.html" %}
{% block page_title %}{{ quiz.title }}{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{{ quiz.title }}</div>
    <div class="page-sub">{{ quiz.course.code }} · {{ questions_data|length }} question{{ questions_data|length|pluralize }} · {{ attempt.max_score }} marks</div>
  </div>
  {% if has_time_limit %}
    <div id="timer" style="background:#1a5c38;color:#fff;padding:12px 22px;border-radius:10px;font-weight:700;font-size:16px;font-family:monospace;text-align:center;min-width:130px">--:--</div>
  {% endif %}
</div>

{% if quiz.description %}
  <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:14px 18px;margin-bottom:16px;color:#1e40af;font-size:13px">
    <strong>Instructions:</strong> {{ quiz.description|linebreaksbr }}
  </div>
{% endif %}

<form method="post" id="quizForm">
  {% csrf_token %}
  {% for item in questions_data %}
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin-bottom:14px">
      <div style="font-weight:600;color:#111;font-size:14px;margin-bottom:12px">
        <span style="background:#1a5c38;color:#fff;padding:2px 8px;border-radius:99px;font-size:11px;margin-right:8px">Q{{ forloop.counter }}</span>
        {{ item.question.text }}
      </div>
      {% for choice in item.choices %}
        <label style="display:block;padding:11px 14px;border:1px solid #e5e7eb;border-radius:8px;margin-bottom:6px;cursor:pointer;font-size:13px;transition:background .12s" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background=''">
          <input type="radio" name="q_{{ item.question.id }}" value="{{ choice.id }}" style="margin-right:10px;accent-color:#1a5c38" {% if item.answer.selected_choice_id == choice.id %}checked{% endif %}>
          {{ choice.text }}
        </label>
      {% endfor %}
    </div>
  {% endfor %}

  <div style="background:#fff;border-top:3px solid #1a5c38;padding:18px;text-align:center;border-radius:0 0 12px 12px;margin-top:16px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb">
    <button type="submit" style="background:#1a5c38;color:#fff;border:none;padding:13px 36px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer">Submit Quiz</button>
    <div style="margin-top:8px;font-size:12px;color:#6b7280">Once submitted, you cannot retake this quiz.</div>
  </div>
</form>

<script>
  let submitting = false;
  window.addEventListener('beforeunload', e => { if (!submitting) { e.preventDefault(); e.returnValue = ''; } });
  document.getElementById('quizForm').addEventListener('submit', () => submitting = true);
  {% if has_time_limit %}
  let remaining = {{ remaining_seconds }};
  const timer = document.getElementById('timer');
  function tick(){
    if (remaining <= 0){ timer.textContent = "Time up!"; submitting = true; document.getElementById('quizForm').submit(); return; }
    const m = Math.floor(remaining/60), s = remaining%60;
    timer.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    if (remaining < 60) timer.style.background = '#dc2626';
    else if (remaining < 300) timer.style.background = '#c8881a';
    remaining--;
  }
  tick(); setInterval(tick, 1000);
  {% endif %}
</script>
{% endblock %}
'''

QUIZ_RESULT = r'''{% extends "base.html" %}
{% block page_title %}Quiz Result{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{{ quiz.title }} — Result</div>
    <div class="page-sub">{{ quiz.course.code }} · {{ quiz.semester }}</div>
  </div>
  <a href="{% url 'lecturers:student_quiz_list' %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:9px 18px;border-radius:8px;font-size:13px;text-decoration:none">← All quizzes</a>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:32px;text-align:center;max-width:640px">
  {% if show_score %}
    <div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Your Score</div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:72px;font-weight:700;color:#1a5c38;line-height:1">
      {{ attempt.score }}<span style="font-size:32px;color:#9ca3af"> / {{ attempt.max_score }}</span>
    </div>
    <div style="margin-top:16px;color:#374151;font-size:14px">
      You answered {{ attempt.correct_count }} of {{ attempt.question_count }} question{{ attempt.question_count|pluralize }} correctly.
    </div>
    {% if attempt.auto_submitted %}
      <div style="margin-top:14px;padding:8px 14px;background:#fef3c7;color:#92400e;border-radius:8px;display:inline-block;font-size:12px">⏰ This attempt was auto-submitted when time ran out.</div>
    {% endif %}
  {% else %}
    <div style="font-size:56px;margin-bottom:14px">✅</div>
    <div style="font-size:18px;font-weight:600;color:#111;margin-bottom:6px">Submitted successfully</div>
    <div style="font-size:14px;color:#6b7280">Your result will be released on <strong>{{ quiz.available_until|date:"d M Y, H:i" }}</strong>, once this quiz closes for everyone.</div>
  {% endif %}
  <div style="margin-top:24px;padding-top:18px;border-top:1px solid #f3f4f6;font-size:12px;color:#9ca3af">
    Submitted: {{ attempt.submitted_at|date:"d M Y, H:i" }}
  </div>
</div>
{% endblock %}
'''


# ========== SIDEBAR ENTRY ==========
def patch_student_sidebar(c):
    if "'lecturers:student_quiz_list'" in c:
        return None, 'Available Quizzes already in student sidebar'
    pat = r"(<a href=\"\{%\s*url\s+'my_courses'\s*%\}\".*?</a>\s*\n)"
    m = re.search(pat, c)
    if not m:
        return None, 'could not find my_courses anchor (student section)'
    link = "  <a href=\"{% url 'lecturers:student_quiz_list' %}\" class=\"nav-item {% if request.resolver_match.url_name == 'student_quiz_list' or request.resolver_match.url_name == 'quiz_take' or request.resolver_match.url_name == 'quiz_attempt_result' %}active{% endif %}\"><div class=\"nav-icon\"><i class=\"bi bi-patch-question\"></i></div>Available Quizzes</a>\n"
    return c[:m.end()] + link + c[m.end():], 'inserted Available Quizzes into student sidebar'


# ========== APPLY ==========
def patch_file(path, label, fn):
    if not path.exists():
        print(f'  ✗ {label}: not found'); return
    c = path.read_text(encoding='utf-8')
    new, msg = fn(c)
    if new is None:
        print(f'  • {label}: {msg}')
    else:
        path.write_text(new, encoding='utf-8')
        print(f'  ✓ {label}: {msg}')


def write_template(path, content, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'  ✓ wrote {label}')


print('\n=== Phase 1B.2 patcher ===\n')

print('[1/5] lecturers/models.py (append QuizAttempt + AttemptAnswer):')
def p_models(c):
    if 'class QuizAttempt(' in c: return None, 'QuizAttempt already present'
    return c.rstrip() + MODELS_ADDITION + '\n', 'appended QuizAttempt + AttemptAnswer'
patch_file(ROOT / 'lecturers/models.py', 'models.py', p_models)

print('\n[2/5] lecturers/views.py (append student views):')
def p_views(c):
    if 'def student_quiz_list(' in c: return None, 'student quiz views already present'
    return c.rstrip() + VIEWS_ADDITION + '\n', 'appended 4 student-side views + decorator'
patch_file(ROOT / 'lecturers/views.py', 'views.py', p_views)

print('\n[3/5] lecturers/urls.py (append 4 student URLs):')
def p_urls(c):
    if "name='student_quiz_list'" in c: return None, 'student URLs already present'
    m = re.search(r'(urlpatterns\s*=\s*\[)(.*?)(\n\])', c, flags=re.DOTALL)
    if not m: return None, 'could not find urlpatterns list'
    return c[:m.end(2)] + '\n' + URL_LINES + c[m.start(3):], 'inserted 4 student-quiz URL patterns'
patch_file(ROOT / 'lecturers/urls.py', 'urls.py', p_urls)

print('\n[4/5] templates:')
write_template(ROOT / 'lecturers/templates/lecturers/student_quiz_list.html', STUDENT_QUIZ_LIST, 'student_quiz_list.html')
write_template(ROOT / 'lecturers/templates/lecturers/take_quiz.html',         TAKE_QUIZ,         'take_quiz.html')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_result.html',       QUIZ_RESULT,       'quiz_result.html')

print('\n[5/5] templates/base.html (student sidebar entry):')
patch_file(ROOT / 'templates/base.html', 'base.html', patch_student_sidebar)

print('\n=== DONE ===')
print('\nNow run:')
print('  python manage.py makemigrations lecturers')
print('  python manage.py migrate')
print('  python manage.py check')
print('  touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')