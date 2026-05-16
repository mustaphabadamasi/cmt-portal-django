#!/usr/bin/env python3
"""Phase 1B.3 — Lecturer results dashboard + CA aggregation. Idempotent."""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')


# ========== VIEWS ADDITION ==========
VIEWS_ADDITION = r'''

# ============================================================
# Phase 1B.3 — Results & CA Aggregation (lecturer-facing)
# ============================================================

def _can_view_results(user, quiz):
    if user.is_superuser: return True
    if getattr(user, 'role', None) in ('admin', 'registrar', 'academic_officer'): return True
    if getattr(user, 'role', None) == 'lecturer' and hasattr(user, 'lecturer'):
        return quiz.created_by_id == user.lecturer.id
    return False


def _can_view_course_results(user, course, semester):
    if user.is_superuser: return True
    if getattr(user, 'role', None) in ('admin', 'registrar', 'academic_officer'): return True
    if getattr(user, 'role', None) == 'lecturer' and hasattr(user, 'lecturer'):
        return LecturerCourse.objects.filter(
            lecturer=user.lecturer, course=course, semester=semester, is_active=True
        ).exists()
    return False


@login_required
def quiz_attempts(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related('course', 'semester'), pk=pk)
    if not _can_view_results(request.user, quiz):
        return HttpResponseForbidden("You don't have permission to view these attempts.")
    attempts = list(QuizAttempt.objects
                    .filter(quiz=quiz)
                    .select_related('student', 'student__user')
                    .order_by('-is_submitted', '-score', 'student__reg_number'))
    submitted = [a for a in attempts if a.is_submitted]
    n = len(submitted)
    avg = round(sum(float(a.score or 0) for a in submitted) / n, 2) if n else 0
    hi  = round(max((float(a.score or 0) for a in submitted), default=0), 2)
    lo  = round(min((float(a.score or 0) for a in submitted), default=0), 2)
    return render(request, 'lecturers/quiz_attempts.html', {
        'quiz': quiz, 'attempts': attempts,
        'submitted_count': n,
        'in_progress_count': len(attempts) - n,
        'avg_score': avg, 'hi': hi, 'lo': lo,
    })


@login_required
def attempt_inspect(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'quiz__course', 'quiz__semester', 'student', 'student__user'),
        pk=pk,
    )
    if not _can_view_results(request.user, attempt.quiz):
        return HttpResponseForbidden("You don't have permission.")
    answers = list(attempt.answers
                   .select_related('question', 'selected_choice')
                   .prefetch_related('question__choices')
                   .order_by('order'))
    items = []
    for a in answers:
        choices = list(a.question.choices.all())
        correct = next((c for c in choices if c.is_correct), None)
        items.append({'answer': a, 'question': a.question, 'choices': choices, 'correct': correct})
    return render(request, 'lecturers/attempt_inspect.html', {
        'attempt': attempt, 'quiz': attempt.quiz, 'items': items,
    })


@login_required
def course_results(request, course_id, semester_id):
    from academics.models import Course, CourseRegistration
    from core.models import Semester
    course   = get_object_or_404(Course, pk=course_id)
    semester = get_object_or_404(Semester, pk=semester_id)
    if not _can_view_course_results(request.user, course, semester):
        return HttpResponseForbidden("You are not assigned to this course.")
    quizzes = list(Quiz.objects.filter(course=course, semester=semester, is_published=True).order_by('available_from'))
    regs = (CourseRegistration.objects
            .filter(course=course, semester=semester, status__in=['registered', 'carryover'])
            .select_related('student', 'student__user')
            .order_by('student__reg_number'))
    score_map = {(a.student_id, a.quiz_id): a for a in
                 QuizAttempt.objects.filter(quiz__in=quizzes, is_submitted=True)}
    max_total = sum(q.max_score for q in quizzes)
    rows = []
    for r in regs:
        s = r.student
        cells = []
        total = 0.0
        for q in quizzes:
            att = score_map.get((s.id, q.id))
            cells.append({'quiz': q, 'attempt': att, 'score': att.score if att else None})
            if att and att.score is not None:
                total += float(att.score)
        rows.append({'student': s, 'cells': cells, 'total': round(total, 2)})
    rows.sort(key=lambda r: -r['total'])
    return render(request, 'lecturers/course_results.html', {
        'course': course, 'semester': semester,
        'quizzes': quizzes, 'rows': rows, 'max_total': max_total,
    })
'''


# ========== URL ADDITIONS ==========
URL_LINES = """    path('quizzes/<int:pk>/attempts/',                            views.quiz_attempts,   name='quiz_attempts'),
    path('attempts/<int:pk>/inspect/',                            views.attempt_inspect, name='attempt_inspect'),
    path('course-results/<int:course_id>/<int:semester_id>/',     views.course_results,  name='course_results'),
"""


# ========== TEMPLATES ==========
QUIZ_ATTEMPTS = r'''{% extends "base.html" %}
{% block page_title %}{{ quiz.title }} — Attempts{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{{ quiz.title }} — Attempts</div>
    <div class="page-sub">{{ quiz.course.code }} · {{ quiz.semester }}</div>
  </div>
  <div style="display:flex;gap:8px">
    <a href="{% url 'lecturers:course_results' quiz.course_id quiz.semester_id %}" style="background:#fff;color:#1a5c38;border:1px solid #bbf7d0;padding:9px 16px;border-radius:8px;font-size:13px;text-decoration:none;font-weight:600">📊 Course Results</a>
    <a href="{% url 'lecturers:quiz_detail' quiz.pk %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:9px 16px;border-radius:8px;font-size:13px;text-decoration:none">← Quiz</a>
  </div>
</div>

<style>
  .statgrid{display:grid;grid-template-columns:repeat(5, 1fr);gap:12px;margin-bottom:18px}
  .scard{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px}
  .scard .lbl{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}
  .scard .val{font-size:24px;font-weight:700;color:#1a5c38;font-family:'Space Grotesk',sans-serif}
  table.attempts{width:100%;background:#fff;border:1px solid #e5e7eb;border-radius:12px;border-collapse:collapse;overflow:hidden}
  table.attempts th{background:#f9fafb;padding:11px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #e5e7eb}
  table.attempts td{padding:12px 14px;font-size:13px;border-bottom:1px solid #f3f4f6;color:#111}
  table.attempts tr:hover td{background:#fafafa}
  .score-pill{background:#d1fae5;color:#065f46;padding:3px 10px;border-radius:99px;font-weight:700;font-size:12px;display:inline-block}
  .score-pill.low{background:#fee2e2;color:#991b1b}
  .pill-auto{background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600}
  .pill-prog{background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600}
</style>

<div class="statgrid">
  <div class="scard"><div class="lbl">Submitted</div><div class="val">{{ submitted_count }}</div></div>
  <div class="scard"><div class="lbl">In Progress</div><div class="val">{{ in_progress_count }}</div></div>
  <div class="scard"><div class="lbl">Average</div><div class="val">{{ avg_score }}</div></div>
  <div class="scard"><div class="lbl">Highest</div><div class="val">{{ hi }}</div></div>
  <div class="scard"><div class="lbl">Lowest</div><div class="val">{{ lo }}</div></div>
</div>

<table class="attempts">
  <thead>
    <tr>
      <th>#</th><th>Student</th><th>Reg No.</th>
      <th>Score</th><th>Submitted</th><th></th><th></th>
    </tr>
  </thead>
  <tbody>
    {% for a in attempts %}
      <tr>
        <td>{{ forloop.counter }}</td>
        <td>{{ a.student.user.last_name|upper }} {{ a.student.user.first_name }}</td>
        <td>{{ a.student.reg_number }}</td>
        <td>
          {% if a.is_submitted %}
            {% with pct=a.score %}
              <span class="score-pill {% if pct < a.max_score|add:'-1'|floatformat:'-2' %}{% endif %}">{{ a.score }} / {{ a.max_score }}</span>
            {% endwith %}
          {% else %}<span style="color:#9ca3af">—</span>{% endif %}
        </td>
        <td>{% if a.submitted_at %}{{ a.submitted_at|date:"d M, H:i" }}{% else %}<span style="color:#9ca3af">—</span>{% endif %}</td>
        <td>
          {% if not a.is_submitted %}<span class="pill-prog">IN PROGRESS</span>{% endif %}
          {% if a.auto_submitted %}<span class="pill-auto">⏰ AUTO</span>{% endif %}
        </td>
        <td><a href="{% url 'lecturers:attempt_inspect' a.pk %}" style="color:#1a5c38;font-weight:600;text-decoration:none">View →</a></td>
      </tr>
    {% empty %}
      <tr><td colspan="7" style="text-align:center;padding:40px;color:#9ca3af">No attempts yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
'''

ATTEMPT_INSPECT = r'''{% extends "base.html" %}
{% block page_title %}Review attempt{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{{ attempt.student.user.last_name|upper }} {{ attempt.student.user.first_name }}</div>
    <div class="page-sub">{{ attempt.student.reg_number }} · {{ quiz.title }} · {{ quiz.course.code }}</div>
  </div>
  <a href="{% url 'lecturers:quiz_attempts' quiz.pk %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:9px 16px;border-radius:8px;font-size:13px;text-decoration:none">← All attempts</a>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:22px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
  <div>
    <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px">Final Score</div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:48px;font-weight:700;color:#1a5c38;line-height:1">
      {{ attempt.score }}<span style="font-size:22px;color:#9ca3af"> / {{ attempt.max_score }}</span>
    </div>
  </div>
  <div style="text-align:right;font-size:13px;color:#374151">
    <div><strong>{{ attempt.correct_count }}</strong> of {{ attempt.question_count }} correct</div>
    <div style="color:#6b7280;font-size:12px;margin-top:4px">Submitted: {{ attempt.submitted_at|date:"d M Y, H:i" }}</div>
    {% if attempt.auto_submitted %}<div style="margin-top:6px"><span style="background:#fef3c7;color:#92400e;padding:3px 9px;border-radius:99px;font-size:11px;font-weight:600">⏰ Auto-submitted</span></div>{% endif %}
  </div>
</div>

{% for item in items %}
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin-bottom:12px">
    <div style="font-weight:600;color:#111;font-size:14px;margin-bottom:12px">
      <span style="background:{% if item.answer.is_correct %}#16a34a{% else %}#dc2626{% endif %};color:#fff;padding:2px 9px;border-radius:99px;font-size:11px;margin-right:8px">Q{{ forloop.counter }}</span>
      {{ item.question.text }}
      <span style="float:right;font-size:11px;color:#9ca3af;font-weight:400">{% if item.answer.is_correct %}✓ correct{% else %}✗ wrong{% endif %}</span>
    </div>
    {% for c in item.choices %}
      <div style="padding:9px 14px;border-radius:8px;margin-bottom:5px;font-size:13px;border:1px solid #e5e7eb;
        {% if c.is_correct %}background:#ecfdf5;border-color:#86efac;{% endif %}
        {% if item.answer.selected_choice_id == c.id and not c.is_correct %}background:#fef2f2;border-color:#fca5a5;{% endif %}
      ">
        {{ c.text }}
        {% if c.is_correct %}<span style="float:right;color:#065f46;font-size:11px;font-weight:600">✓ correct answer</span>{% endif %}
        {% if item.answer.selected_choice_id == c.id %}<span style="float:right;margin-right:8px;color:#1f2937;font-size:11px;font-weight:600">← student picked</span>{% endif %}
      </div>
    {% endfor %}
    {% if not item.answer.selected_choice_id %}
      <div style="margin-top:6px;padding:8px;background:#f9fafb;color:#6b7280;border-radius:6px;font-size:12px;font-style:italic">Not answered</div>
    {% endif %}
  </div>
{% endfor %}
{% endblock %}
'''

COURSE_RESULTS = r'''{% extends "base.html" %}
{% block page_title %}{{ course.code }} Results{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">{{ course.code }} — Class Results</div>
    <div class="page-sub">{{ course.title }} · {{ semester }} · {{ rows|length }} registered student{{ rows|length|pluralize }}</div>
  </div>
</div>

<style>
  table.results{width:100%;background:#fff;border:1px solid #e5e7eb;border-radius:12px;border-collapse:collapse;overflow:hidden;font-size:13px}
  table.results th{background:#1a5c38;color:#fff;padding:11px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.3px;font-weight:600}
  table.results th.num{text-align:center}
  table.results td{padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#111}
  table.results td.num{text-align:center;font-variant-numeric:tabular-nums}
  table.results tr:hover td{background:#fafafa}
  table.results td.tot{font-weight:700;color:#1a5c38;background:#f9fafb}
  table.results td.miss{color:#9ca3af}
</style>

{% if quizzes %}
<div style="overflow-x:auto">
<table class="results">
  <thead>
    <tr>
      <th>#</th>
      <th>Reg No.</th>
      <th>Student</th>
      {% for q in quizzes %}<th class="num" title="{{ q.title }}">{{ q.title|truncatechars:18 }}<br><span style="font-weight:400;opacity:.7">/{{ q.max_score }}</span></th>{% endfor %}
      <th class="num">Quiz Total<br><span style="font-weight:400;opacity:.7">/{{ max_total }}</span></th>
      <th class="num">Assignments<br><span style="font-weight:400;opacity:.7">(Phase 1C)</span></th>
      <th class="num">CA</th>
    </tr>
  </thead>
  <tbody>
    {% for r in rows %}
      <tr>
        <td class="num">{{ forloop.counter }}</td>
        <td>{{ r.student.reg_number }}</td>
        <td>{{ r.student.user.last_name|upper }} {{ r.student.user.first_name }}</td>
        {% for cell in r.cells %}
          <td class="num {% if not cell.attempt %}miss{% endif %}">
            {% if cell.attempt %}{{ cell.score }}{% else %}—{% endif %}
          </td>
        {% endfor %}
        <td class="num tot">{{ r.total }}</td>
        <td class="num miss">—</td>
        <td class="num tot">{{ r.total }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
</div>

<div style="font-size:12px;color:#6b7280;margin-top:14px;line-height:1.5">
  <strong>CA</strong> currently equals the sum of all quiz scores. Once Phase 1C ships, the Assignments column will populate and CA will reflect both. Dash (—) means the student didn't take that quiz.
</div>
{% else %}
<div style="background:#fff;border:1px dashed #e5e7eb;border-radius:12px;padding:48px;text-align:center;color:#9ca3af">
  <i class="bi bi-bar-chart" style="font-size:48px;display:block;margin-bottom:10px"></i>
  No published quizzes for this course yet. Publish a quiz to start seeing results here.
</div>
{% endif %}
{% endblock %}
'''


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


print('\n=== Phase 1B.3 patcher ===\n')

print('[1/4] lecturers/views.py (append 3 views + 2 helpers):')
def p_views(c):
    if 'def quiz_attempts(' in c: return None, 'results views already present'
    return c.rstrip() + VIEWS_ADDITION + '\n', 'appended 3 views + permission helpers'
patch_file(ROOT / 'lecturers/views.py', 'views.py', p_views)

print('\n[2/4] lecturers/urls.py (append 3 URLs):')
def p_urls(c):
    if "name='quiz_attempts'" in c: return None, 'results URLs already present'
    m = re.search(r'(urlpatterns\s*=\s*\[)(.*?)(\n\])', c, flags=re.DOTALL)
    if not m: return None, 'could not find urlpatterns list'
    return c[:m.end(2)] + '\n' + URL_LINES + c[m.start(3):], 'inserted 3 results URL patterns'
patch_file(ROOT / 'lecturers/urls.py', 'urls.py', p_urls)

print('\n[3/4] templates:')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_attempts.html',  QUIZ_ATTEMPTS,   'quiz_attempts.html')
write_template(ROOT / 'lecturers/templates/lecturers/attempt_inspect.html', ATTEMPT_INSPECT, 'attempt_inspect.html')
write_template(ROOT / 'lecturers/templates/lecturers/course_results.html',  COURSE_RESULTS,  'course_results.html')

print('\n[4/4] quiz_detail.html (add View Attempts button):')
def p_qdet(c):
    if 'lecturers:quiz_attempts' in c: return None, 'View Attempts button already present'
    # Anchor: the Import CSV link added in 1B.1c. Insert View Attempts button right before it.
    pat = re.compile(r"<a\b(?:(?!</a>)[\s\S])*?lecturers:quiz_import(?:(?!</a>)[\s\S])*?</a>")
    m = pat.search(c)
    if not m:
        return None, 'could not find Import CSV anchor in quiz_detail.html'
    btn = ("<a href=\"{% url 'lecturers:quiz_attempts' quiz.pk %}\" "
           "style=\"background:#1a5c38;color:#fff;border:none;padding:9px 16px;border-radius:8px;"
           "font-size:13px;text-decoration:none;font-weight:600;margin-right:6px\">"
           "📊 View Attempts</a>\n        ")
    return c[:m.start()] + btn + c[m.start():], 'inserted View Attempts button before Import CSV'
patch_file(ROOT / 'lecturers/templates/lecturers/quiz_detail.html', 'quiz_detail.html', p_qdet)

print('\n=== DONE ===')
print('\nNow run:')
print('  python manage.py check')
print('  touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')