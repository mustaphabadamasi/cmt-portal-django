#!/usr/bin/env python3
"""
Phase 1B.1b — Lecturer-side quiz management UI.
Appends forms/views/URLs, creates 3 templates, edits base.html sidebar.
Idempotent.
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')


# ========== FORMS ==========
FORMS_ADDITION = r'''

# ============================================================
# Phase 1B — Quiz forms
# ============================================================
from .models import Quiz, Question, Choice


class QuizForm(forms.ModelForm):
    """Course/Semester dropdowns are filtered to the lecturer's active assignments."""

    class Meta:
        model = Quiz
        fields = ['course', 'semester', 'title', 'description',
                  'max_score', 'time_limit_minutes',
                  'available_from', 'available_until']
        widgets = {
            'description':     forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional instructions shown to students before they start.'}),
            'available_from':  forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, lecturer=None, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing instance, datetime-local widget needs ISO format
        for f in ('available_from', 'available_until'):
            if self.instance and getattr(self.instance, f, None):
                self.initial[f] = getattr(self.instance, f).strftime('%Y-%m-%dT%H:%M')
        if lecturer is not None:
            from .models import LecturerCourse
            qs = LecturerCourse.objects.filter(lecturer=lecturer, is_active=True)
            self.fields['course'].queryset   = self.fields['course'].queryset.filter(id__in=qs.values_list('course_id', flat=True))
            self.fields['semester'].queryset = self.fields['semester'].queryset.filter(id__in=qs.values_list('semester_id', flat=True))

    def clean(self):
        cleaned = super().clean()
        af, au = cleaned.get('available_from'), cleaned.get('available_until')
        if af and au and au <= af:
            raise forms.ValidationError("'Available until' must be after 'Available from'.")
        return cleaned


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'points']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Question text...'})}


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text']
        widgets = {'text': forms.TextInput(attrs={'placeholder': 'Option text...'})}
'''


# ========== VIEWS ==========
VIEWS_ADDITION = r'''

# ============================================================
# Phase 1B — Quiz lecturer-side views
# ============================================================
from django.db import transaction as _qtx
from .models import Quiz, Question, Choice
from .forms import QuizForm, QuestionForm, ChoiceForm


def _own_quiz_or_403(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related('course', 'semester', 'created_by'), pk=pk)
    if quiz.created_by != request.user.lecturer_profile:
        return None, HttpResponseForbidden("This quiz isn't yours.")
    return quiz, None


@lecturer_required
def quiz_list(request):
    lecturer = request.user.lecturer_profile
    quizzes = (Quiz.objects.filter(created_by=lecturer)
               .select_related('course', 'semester').order_by('-created_at'))
    return render(request, 'lecturers/quiz_list.html', {'lecturer': lecturer, 'quizzes': quizzes})


@lecturer_required
def quiz_create(request):
    lecturer = request.user.lecturer_profile
    if request.method == 'POST':
        form = QuizForm(request.POST, lecturer=lecturer)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = lecturer
            quiz.save()
            messages.success(request, f"Created '{quiz.title}'. Now add its questions and choices.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    else:
        form = QuizForm(lecturer=lecturer)
    return render(request, 'lecturers/quiz_form.html', {'form': form, 'mode': 'create'})


@lecturer_required
def quiz_update(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz, lecturer=request.user.lecturer_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz settings updated.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    else:
        form = QuizForm(instance=quiz, lecturer=request.user.lecturer_profile)
    return render(request, 'lecturers/quiz_form.html', {'form': form, 'mode': 'update', 'quiz': quiz})


@lecturer_required
def quiz_detail(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    questions = quiz.questions.prefetch_related('choices').order_by('order', 'id')
    return render(request, 'lecturers/quiz_detail.html', {
        'quiz': quiz, 'questions': questions,
        'question_form': QuestionForm(), 'choice_form': ChoiceForm(),
    })


@lecturer_required
def quiz_publish(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method != 'POST':
        return redirect('lecturers:quiz_detail', pk=quiz.pk)
    if not quiz.is_published:
        if quiz.questions.count() == 0:
            messages.error(request, "Add at least one question before publishing.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
        bad = [q for q in quiz.questions.prefetch_related('choices') if not q.is_ready]
        if bad:
            messages.error(request, f"{len(bad)} question(s) need at least 2 choices and exactly one marked correct.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    quiz.is_published = not quiz.is_published
    quiz.save(update_fields=['is_published', 'updated_at'])
    messages.success(request, f"Quiz {'published' if quiz.is_published else 'unpublished'}.")
    return redirect('lecturers:quiz_detail', pk=quiz.pk)


@lecturer_required
def quiz_delete(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        title = quiz.title
        quiz.delete()
        messages.info(request, f"Deleted '{title}'.")
        return redirect('lecturers:quiz_list')
    return redirect('lecturers:quiz_detail', pk=pk)


@lecturer_required
def question_create(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.quiz = quiz
            q.order = quiz.questions.count() + 1
            q.save()
            messages.success(request, "Question added. Now add at least 2 choices and mark one correct.")
        else:
            for f, errs in form.errors.items():
                for e in errs: messages.error(request, f"{f}: {e}")
    return redirect('lecturers:quiz_detail', pk=pk)


@lecturer_required
def question_delete(request, pk):
    question = get_object_or_404(Question.objects.select_related('quiz'), pk=pk)
    if question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your question.")
    quiz_pk = question.quiz_id
    if request.method == 'POST':
        question.delete()
        messages.info(request, "Question removed.")
    return redirect('lecturers:quiz_detail', pk=quiz_pk)


@lecturer_required
def choice_create(request, pk):
    question = get_object_or_404(Question.objects.select_related('quiz'), pk=pk)
    if question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your question.")
    if request.method == 'POST':
        form = ChoiceForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.question = question
            c.order = question.choices.count() + 1
            c.save()
        else:
            for f, errs in form.errors.items():
                for e in errs: messages.error(request, f"{f}: {e}")
    return redirect('lecturers:quiz_detail', pk=question.quiz_id)


@lecturer_required
def choice_delete(request, pk):
    choice = get_object_or_404(Choice.objects.select_related('question__quiz'), pk=pk)
    if choice.question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your choice.")
    quiz_pk = choice.question.quiz_id
    if request.method == 'POST':
        choice.delete()
    return redirect('lecturers:quiz_detail', pk=quiz_pk)


@lecturer_required
def choice_mark_correct(request, pk):
    choice = get_object_or_404(Choice.objects.select_related('question__quiz'), pk=pk)
    if choice.question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your choice.")
    if request.method == 'POST':
        with _qtx.atomic():
            choice.question.choices.update(is_correct=False)
            choice.is_correct = True
            choice.save(update_fields=['is_correct'])
    return redirect('lecturers:quiz_detail', pk=choice.question.quiz_id)
'''


# ========== URL PATTERNS ==========
URLS_ADDITION = """    path('quizzes/',                       views.quiz_list,           name='quiz_list'),
    path('quizzes/new/',                   views.quiz_create,         name='quiz_create'),
    path('quizzes/<int:pk>/',              views.quiz_detail,         name='quiz_detail'),
    path('quizzes/<int:pk>/edit/',         views.quiz_update,         name='quiz_update'),
    path('quizzes/<int:pk>/delete/',       views.quiz_delete,         name='quiz_delete'),
    path('quizzes/<int:pk>/publish/',      views.quiz_publish,        name='quiz_publish'),
    path('quizzes/<int:pk>/question/add/', views.question_create,     name='question_create'),
    path('questions/<int:pk>/delete/',     views.question_delete,     name='question_delete'),
    path('questions/<int:pk>/choice/add/', views.choice_create,       name='choice_create'),
    path('choices/<int:pk>/delete/',       views.choice_delete,       name='choice_delete'),
    path('choices/<int:pk>/correct/',      views.choice_mark_correct, name='choice_mark_correct'),
"""


# ========== TEMPLATES ==========
QUIZ_LIST_HTML = r'''{% extends "base.html" %}
{% block page_title %}My Quizzes{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">My Quizzes</div>
    <div class="page-sub">{{ quizzes|length }} quiz{{ quizzes|length|pluralize:"zes" }} across your assigned courses.</div>
  </div>
  <a href="{% url 'lecturers:quiz_create' %}" style="background:#1a5c38;color:#fff;text-decoration:none;padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600">+ New Quiz</a>
</div>

<style>
  .qz-tbl{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;font-size:13px}
  .qz-tbl th{background:#1a5c38;color:#fff;padding:10px 14px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.5px;font-weight:500}
  .qz-tbl td{padding:11px 14px;border-bottom:1px solid #f3f4f6;vertical-align:middle}
  .qz-tbl tr:hover td{background:#f9fafb}
  .stat-pill{display:inline-block;padding:2px 9px;border-radius:99px;font-size:10px;font-weight:700;letter-spacing:.3px}
  .stat-draft   {background:#e5e7eb;color:#374151}
  .stat-upcoming{background:#dbeafe;color:#1e40af}
  .stat-open    {background:#d1fae5;color:#065f46}
  .stat-closed  {background:#fee2e2;color:#991b1b}
</style>

<table class="qz-tbl">
  <thead>
    <tr><th>#</th><th>Title</th><th>Course</th><th>Semester</th><th>Qs</th><th>Window</th><th>Status</th><th></th></tr>
  </thead>
  <tbody>
    {% for q in quizzes %}
      <tr>
        <td>{{ forloop.counter }}</td>
        <td style="font-weight:600">{{ q.title }}</td>
        <td>{{ q.course.code }}</td>
        <td>{{ q.semester }}</td>
        <td>{{ q.question_count }}</td>
        <td style="font-size:11px;color:#6b7280">{{ q.available_from|date:"d M, H:i" }} → {{ q.available_until|date:"d M, H:i" }}</td>
        <td><span class="stat-pill stat-{{ q.status }}">{{ q.status|upper }}</span></td>
        <td><a href="{% url 'lecturers:quiz_detail' q.pk %}" style="color:#1a5c38;font-weight:600;text-decoration:none">Open →</a></td>
      </tr>
    {% empty %}
      <tr><td colspan="8" style="text-align:center;color:#9ca3af;padding:40px"><i class="bi bi-patch-question" style="font-size:36px;display:block;margin-bottom:8px"></i>No quizzes yet. Click "+ New Quiz" to create one.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
'''


QUIZ_FORM_HTML = r'''{% extends "base.html" %}
{% block page_title %}{% if mode == 'create' %}New Quiz{% else %}Edit Quiz{% endif %}{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{% if mode == 'create' %}New Quiz{% else %}Edit: {{ quiz.title }}{% endif %}</div>
    <div class="page-sub">Quiz settings · You can add questions after creation.</div>
  </div>
  <a href="{% url 'lecturers:quiz_list' %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:9px 18px;border-radius:8px;font-size:13px;text-decoration:none">← Back</a>
</div>

<style>
  .qf{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:22px;max-width:780px}
  .qf .g{margin-bottom:14px}
  .qf label{display:block;font-size:11px;font-weight:600;color:#6b7280;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
  .qf input, .qf select, .qf textarea{width:100%;padding:10px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;font-family:inherit}
  .qf .h{font-size:11px;color:#9ca3af;margin-top:3px}
  .qf .e{font-size:12px;color:#991b1b;margin-top:3px}
  .qf .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
</style>

<form method="post" class="qf">
  {% csrf_token %}
  {% if form.non_field_errors %}
    <div style="background:#fee2e2;color:#991b1b;padding:10px 14px;border-radius:8px;margin-bottom:14px;font-size:13px">{{ form.non_field_errors }}</div>
  {% endif %}

  <div class="row">
    <div class="g"><label>Course</label>{{ form.course }}{% if form.course.errors %}<div class="e">{{ form.course.errors|join:", " }}</div>{% endif %}</div>
    <div class="g"><label>Semester</label>{{ form.semester }}{% if form.semester.errors %}<div class="e">{{ form.semester.errors|join:", " }}</div>{% endif %}</div>
  </div>
  <div class="g"><label>Title</label>{{ form.title }}{% if form.title.errors %}<div class="e">{{ form.title.errors|join:", " }}</div>{% endif %}</div>
  <div class="g"><label>Description / Instructions</label>{{ form.description }}{% if form.description.help_text %}<div class="h">{{ form.description.help_text }}</div>{% endif %}</div>
  <div class="row">
    <div class="g"><label>Max Score</label>{{ form.max_score }}<div class="h">{{ form.max_score.help_text }}</div></div>
    <div class="g"><label>Time Limit (minutes)</label>{{ form.time_limit_minutes }}<div class="h">{{ form.time_limit_minutes.help_text }}</div></div>
  </div>
  <div class="row">
    <div class="g"><label>Available From</label>{{ form.available_from }}{% if form.available_from.errors %}<div class="e">{{ form.available_from.errors|join:", " }}</div>{% endif %}</div>
    <div class="g"><label>Available Until</label>{{ form.available_until }}{% if form.available_until.errors %}<div class="e">{{ form.available_until.errors|join:", " }}</div>{% endif %}</div>
  </div>

  <button type="submit" style="background:#1a5c38;color:#fff;border:none;padding:11px 22px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">
    {% if mode == 'create' %}Create Quiz & Add Questions{% else %}Save Changes{% endif %}
  </button>
  <a href="{% url 'lecturers:quiz_list' %}" style="margin-left:8px;color:#6b7280;text-decoration:none">Cancel</a>
</form>
{% endblock %}
'''


QUIZ_DETAIL_HTML = r'''{% extends "base.html" %}
{% block page_title %}{{ quiz.title }}{% endblock %}
{% block content %}
<style>
  .qd-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px;margin-bottom:14px}
  .qd-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:10px}
  .qtitle{font-weight:700;color:#111;font-size:15px}
  .qmeta{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}
  .choice{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:6px;margin-bottom:5px;border:1px solid #e5e7eb}
  .choice.correct{background:#f0fdf4;border-color:#86efac}
  .choice .ctxt{flex:1;font-size:13px;color:#111}
  .choice button{padding:4px 10px;font-size:11px;border-radius:6px;border:none;cursor:pointer;font-weight:500}
  .btn-correct{background:#1a5c38;color:#fff}
  .btn-correct-on{background:#86efac;color:#065f46;cursor:default}
  .btn-rmv{background:#fee2e2;color:#991b1b}
  .inl{display:flex;gap:6px;margin-top:8px}
  .inl input{flex:1;padding:7px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;font-family:inherit}
  .inl button{padding:7px 14px;background:#1a5c38;color:#fff;border:none;border-radius:6px;font-size:13px;cursor:pointer}
  .add-q{background:#f9fafb;border:1px dashed #d1d5db;border-radius:12px;padding:16px}
  .add-q textarea, .add-q input{width:100%;padding:8px 11px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;font-family:inherit;margin-bottom:8px}
  .badge{display:inline-block;padding:2px 9px;border-radius:99px;font-size:10px;font-weight:700;letter-spacing:.4px;margin-left:6px;vertical-align:middle}
  .badge-draft   {background:#e5e7eb;color:#374151}
  .badge-upcoming{background:#dbeafe;color:#1e40af}
  .badge-open    {background:#d1fae5;color:#065f46}
  .badge-closed  {background:#fee2e2;color:#991b1b}
  .sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
  .sgrid label{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#9ca3af;margin-bottom:2px}
  .sgrid > div > div{font-size:13px;color:#111;font-weight:500}
</style>

<div class="page-header">
  <div>
    <div class="page-title">{{ quiz.title }} <span class="badge badge-{{ quiz.status }}">{{ quiz.status|upper }}</span></div>
    <div class="page-sub">{{ quiz.course.code }} — {{ quiz.course.title }} · {{ quiz.semester }}</div>
  </div>
  <div style="display:flex;gap:6px;flex-wrap:wrap">
    <a href="{% url 'lecturers:quiz_list' %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:8px 14px;border-radius:8px;font-size:12px;text-decoration:none">← All</a>
    <a href="{% url 'lecturers:quiz_update' quiz.pk %}" style="background:#fff;color:#1a5c38;border:1px solid #bbf7d0;padding:8px 14px;border-radius:8px;font-size:12px;text-decoration:none;font-weight:500">Edit settings</a>
    <form method="post" action="{% url 'lecturers:quiz_publish' quiz.pk %}" style="display:inline">
      {% csrf_token %}
      <button style="background:{% if quiz.is_published %}#c8881a{% else %}#1a5c38{% endif %};color:#fff;border:none;padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer">
        {% if quiz.is_published %}Unpublish{% else %}Publish{% endif %}
      </button>
    </form>
    <form method="post" action="{% url 'lecturers:quiz_delete' quiz.pk %}" style="display:inline" onsubmit="return confirm('Delete this quiz and all its questions? Cannot be undone.');">
      {% csrf_token %}
      <button style="background:#fee2e2;color:#991b1b;border:1px solid #fecaca;padding:8px 14px;border-radius:8px;font-size:12px;cursor:pointer">Delete</button>
    </form>
  </div>
</div>

<div class="qd-card">
  <div class="qmeta" style="margin-bottom:10px">Quiz Settings</div>
  <div class="sgrid">
    <div><label>Max Score</label><div>{{ quiz.max_score }} marks</div></div>
    <div><label>Time Limit</label><div>{% if quiz.time_limit_minutes %}{{ quiz.time_limit_minutes }} min{% else %}No limit{% endif %}</div></div>
    <div><label>Available From</label><div>{{ quiz.available_from|date:"d M Y, H:i" }}</div></div>
    <div><label>Available Until</label><div>{{ quiz.available_until|date:"d M Y, H:i" }}</div></div>
    <div><label>Questions</label><div>{{ quiz.question_count }} ({{ quiz.total_points }} pts)</div></div>
  </div>
  {% if quiz.description %}
    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #f3f4f6">
      <label style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#9ca3af;display:block;margin-bottom:4px">Instructions</label>
      <div style="font-size:13px;color:#374151">{{ quiz.description|linebreaksbr }}</div>
    </div>
  {% endif %}
</div>

<h3 style="font-family:'Space Grotesk',sans-serif;font-size:18px;margin:24px 0 12px">Questions</h3>

{% for q in questions %}
  <div class="qd-card">
    <div class="qd-head">
      <div>
        <div class="qtitle">{{ forloop.counter }}. {{ q.text }}</div>
        <div class="qmeta">{{ q.points }} pt{{ q.points|pluralize }} · {{ q.choices.count }} choice{{ q.choices.count|pluralize }} · {% if q.is_ready %}<span style="color:#065f46;font-weight:700">Ready</span>{% else %}<span style="color:#92400e;font-weight:700">Needs attention</span>{% endif %}</div>
      </div>
      <form method="post" action="{% url 'lecturers:question_delete' q.pk %}" onsubmit="return confirm('Delete this question?');">
        {% csrf_token %}
        <button class="btn-rmv" style="padding:5px 12px;font-size:11px;border-radius:6px;border:none;cursor:pointer">Remove</button>
      </form>
    </div>

    <div style="margin:10px 0 14px">
      {% for c in q.choices.all %}
        <div class="choice {% if c.is_correct %}correct{% endif %}">
          <div class="ctxt">{{ c.text }}</div>
          {% if c.is_correct %}
            <span class="btn-correct-on">✓ Correct</span>
          {% else %}
            <form method="post" action="{% url 'lecturers:choice_mark_correct' c.pk %}" style="display:inline">
              {% csrf_token %}
              <button class="btn-correct">Mark correct</button>
            </form>
          {% endif %}
          <form method="post" action="{% url 'lecturers:choice_delete' c.pk %}" style="display:inline" onsubmit="return confirm('Remove this choice?');">
            {% csrf_token %}
            <button class="btn-rmv">×</button>
          </form>
        </div>
      {% empty %}
        <div style="color:#9ca3af;font-size:13px;padding:8px 0">No choices yet — add at least 2 below.</div>
      {% endfor %}
    </div>

    <form method="post" action="{% url 'lecturers:choice_create' q.pk %}" class="inl">
      {% csrf_token %}
      <input name="text" placeholder="Add a choice..." required>
      <button>+ Add</button>
    </form>
  </div>
{% empty %}
  <div style="padding:36px;text-align:center;color:#9ca3af;background:#fff;border:1px dashed #e5e7eb;border-radius:12px">
    No questions yet. Add your first one below.
  </div>
{% endfor %}

<div class="add-q">
  <div style="font-weight:600;color:#1a5c38;margin-bottom:10px;font-size:14px">+ Add Question</div>
  <form method="post" action="{% url 'lecturers:question_create' quiz.pk %}">
    {% csrf_token %}
    <textarea name="text" rows="2" placeholder="Question text..." required></textarea>
    <div style="display:flex;gap:10px;align-items:center">
      <label style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px">Points:</label>
      <input type="number" name="points" value="1" min="1" style="width:80px;padding:6px 8px;border:1px solid #d1d5db;border-radius:6px">
      <button type="submit" style="margin-left:auto;background:#1a5c38;color:#fff;border:none;padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer">Add Question</button>
    </div>
  </form>
</div>
{% endblock %}
'''


# ========== APPLY PATCHES ==========

def patch_file(path, label, fn):
    if not path.exists():
        print(f'  ✗ {label}: not found at {path}'); return
    content = path.read_text(encoding='utf-8')
    new, msg = fn(content)
    if new is None:
        print(f'  • {label}: {msg}')
    else:
        path.write_text(new, encoding='utf-8')
        print(f'  ✓ {label}: {msg}')


def write_template(path, content, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'  ✓ wrote {label}')


print('\n=== Phase 1B.1b patcher ===\n')

print('[1/6] lecturers/forms.py:')
def p_forms(c):
    if 'class QuizForm(' in c: return None, 'QuizForm already present'
    return c.rstrip() + FORMS_ADDITION + '\n', 'appended QuizForm, QuestionForm, ChoiceForm'
patch_file(ROOT / 'lecturers/forms.py', 'forms', p_forms)

print('\n[2/6] lecturers/views.py:')
def p_views(c):
    if 'def quiz_list(' in c: return None, 'quiz views already present'
    return c.rstrip() + VIEWS_ADDITION + '\n', 'appended 11 quiz-related views'
patch_file(ROOT / 'lecturers/views.py', 'views', p_views)

print('\n[3/6] lecturers/urls.py:')
def p_urls(c):
    if "name='quiz_list'" in c: return None, 'quiz URLs already present'
    m = re.search(r'(urlpatterns\s*=\s*\[)(.*?)(\n\])', c, flags=re.DOTALL)
    if not m: return None, 'could not find urlpatterns list'
    return c[:m.end(2)] + '\n' + URLS_ADDITION + c[m.start(3):], 'inserted 11 quiz URL patterns'
patch_file(ROOT / 'lecturers/urls.py', 'urls', p_urls)

print('\n[4/6] templates:')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_list.html',   QUIZ_LIST_HTML,   'quiz_list.html')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_form.html',   QUIZ_FORM_HTML,   'quiz_form.html')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_detail.html', QUIZ_DETAIL_HTML, 'quiz_detail.html')

print('\n[5/6] templates/base.html: add My Quizzes link in Academic section')
def p_base_add(c):
    if "'lecturers:quiz_list'" in c: return None, 'My Quizzes link already in sidebar'
    pat = r"(<a href=\"\{%\s*url\s+'lecturers:my_courses'\s*%\}\".*?</a>\s*\n)"
    m = re.search(pat, c)
    if not m: return None, 'could not find My Courses sidebar line'
    link = "  <a href=\"{% url 'lecturers:quiz_list' %}\" class=\"nav-item {% if 'quiz' in request.resolver_match.url_name|default:'' %}active{% endif %}\"><div class=\"nav-icon\"><i class=\"bi bi-patch-question\"></i></div>My Quizzes</a>\n"
    return c[:m.end()] + link + c[m.end():], 'inserted My Quizzes link under My Courses'
patch_file(ROOT / 'templates/base.html', 'base.html (add link)', p_base_add)

print('\n[6/6] templates/base.html: remove My Quizzes SOON placeholder')
def p_base_rmv(c):
    lines = c.split('\n')
    out, removed = [], 0
    for line in lines:
        if ('My Quizzes' in line and 'SOON' in line and 'href="#"' in line):
            removed += 1; continue
        out.append(line)
    if removed == 0: return None, 'no SOON placeholder for My Quizzes found'
    return '\n'.join(out), f'removed {removed} SOON placeholder line(s)'
patch_file(ROOT / 'templates/base.html', 'base.html (remove SOON)', p_base_rmv)

print('\n=== DONE ===')
print('\nNow run:')
print('  python manage.py check')
print('  touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')
print('\nThen log in as Saratu and click "My Quizzes" in the sidebar.')