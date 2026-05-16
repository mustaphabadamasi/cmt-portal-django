#!/usr/bin/env python3
"""
Phase 1B.1c — CSV bulk question import + questions_to_attempt field.
Idempotent.
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')


# ========== MODEL CHANGE ==========
def patch_model(c):
    if 'questions_to_attempt' in c:
        return None, 'already has questions_to_attempt'
    anchor = '\n    is_published = models.BooleanField'
    if anchor not in c:
        return None, 'could not find is_published anchor in Quiz model'
    insertion = '\n    questions_to_attempt = models.PositiveIntegerField(null=True, blank=True, help_text="If set, each student sees this many random questions from the bank. Blank = show all.")\n'
    return c.replace(anchor, insertion + anchor, 1), "added questions_to_attempt to Quiz"


# ========== FORM CHANGE ==========
def patch_form(c):
    if "'questions_to_attempt'" in c:
        return None, 'QuizForm already has questions_to_attempt'
    old = "'max_score', 'time_limit_minutes',"
    new = "'max_score', 'questions_to_attempt', 'time_limit_minutes',"
    if old not in c:
        return None, 'could not find QuizForm fields anchor'
    return c.replace(old, new, 1), 'added field to QuizForm.fields'


# ========== VIEWS APPENDIX ==========
VIEWS_ADDITION = r'''

# ============================================================
# Phase 1B.1c — CSV bulk import of quiz questions
# ============================================================
import csv as _csv
import io as _io


@lecturer_required
def quiz_import_csv(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        f = request.FILES.get('csv_file')
        if not f:
            messages.error(request, "Choose a CSV file to upload.")
            return redirect('lecturers:quiz_import', pk=pk)
        try:
            text = f.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, "File must be UTF-8 encoded CSV.")
            return redirect('lecturers:quiz_import', pk=pk)
        rows = list(_csv.reader(_io.StringIO(text)))
        if not rows:
            messages.error(request, "CSV is empty.")
            return redirect('lecturers:quiz_import', pk=pk)
        # Auto-skip header if it looks like one
        first = rows[0]
        if first and any((c or '').strip().lower() in ('question','correct','correct_answer','answer','option') for c in first):
            rows = rows[1:]
        if not rows:
            messages.error(request, "CSV has only a header row.")
            return redirect('lecturers:quiz_import', pk=pk)
        errors = []
        for i, row in enumerate(rows, start=1):
            if len(row) < 3:
                errors.append(f"Row {i}: need at least 3 columns (question, correct, >=1 wrong option). Got {len(row)}.")
            elif not (row[0] or '').strip():
                errors.append(f"Row {i}: question text is empty.")
            elif not (row[1] or '').strip():
                errors.append(f"Row {i}: correct answer is empty.")
            elif not any((c or '').strip() for c in row[2:]):
                errors.append(f"Row {i}: no wrong options.")
        if errors:
            for e in errors[:10]:
                messages.error(request, e)
            if len(errors) > 10:
                messages.error(request, f"... and {len(errors) - 10} more error(s).")
            return redirect('lecturers:quiz_import', pk=pk)
        created_q = created_c = 0
        with _qtx.atomic():
            base = quiz.questions.count()
            for i, row in enumerate(rows, start=1):
                qtext   = row[0].strip()
                correct = row[1].strip()
                wrongs  = [(c or '').strip() for c in row[2:] if (c or '').strip()]
                q = Question.objects.create(quiz=quiz, text=qtext, points=1, order=base + i)
                created_q += 1
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                created_c += 1
                for j, w in enumerate(wrongs, start=2):
                    Choice.objects.create(question=q, text=w, is_correct=False, order=j)
                    created_c += 1
        messages.success(request, f"Imported {created_q} questions ({created_c} choices total).")
        return redirect('lecturers:quiz_detail', pk=pk)
    return render(request, 'lecturers/quiz_import.html', {'quiz': quiz})
'''


# ========== URL ADDITION ==========
URL_LINE = "    path('quizzes/<int:pk>/import/',       views.quiz_import_csv,     name='quiz_import'),\n"


# ========== TEMPLATE: quiz_import.html ==========
QUIZ_IMPORT_HTML = r'''{% extends "base.html" %}
{% block page_title %}Import Questions{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">Import Questions: {{ quiz.title }}</div>
    <div class="page-sub">{{ quiz.course.code }} · {{ quiz.semester }} · current bank: {{ quiz.question_count }} question{{ quiz.question_count|pluralize }}</div>
  </div>
  <a href="{% url 'lecturers:quiz_detail' quiz.pk %}" style="background:#fff;color:#374151;border:1px solid #d1d5db;padding:9px 18px;border-radius:8px;font-size:13px;text-decoration:none">← Back to quiz</a>
</div>

<style>
  .imp-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:22px;max-width:780px;margin-bottom:14px}
  .imp-card h3{font-family:'Space Grotesk',sans-serif;font-size:16px;margin:0 0 10px}
  .imp-card code{background:#f3f4f6;padding:2px 6px;border-radius:4px;font-size:12px;color:#1f2937}
  .imp-card pre{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px;font-size:12px;color:#374151;overflow-x:auto;font-family:Menlo,Consolas,monospace;line-height:1.55}
  .imp-card .file-input{width:100%;padding:14px;border:2px dashed #d1d5db;border-radius:8px;background:#fafafa;font-family:inherit}
  .imp-card .file-input:hover{border-color:#1a5c38;background:#f0fdf4}
</style>

<div class="imp-card">
  <h3>CSV Format</h3>
  <p style="font-size:13px;color:#6b7280;margin:0 0 10px">Each row creates one question with its choices. <strong>Minimum 3 columns</strong>: question, correct answer, then 1 or more wrong options. Header row (if any) is auto-detected and skipped.</p>
<pre>question,correct,wrong1,wrong2,wrong3
"What is research?","Systematic inquiry","Random search","Wild guess","Library tour"
"Capital of Nigeria?","Abuja","Lagos","Kano","Port Harcourt"
"2 + 2 = ?","4","3","5","22"</pre>
  <ul style="font-size:12px;color:#6b7280;margin:10px 0 0;padding-left:18px;line-height:1.7">
    <li>Wrap any cell containing a comma in <code>"double quotes"</code>.</li>
    <li>Each question gets <strong>1 point</strong>. Set the total weighting via the quiz's <em>Max Score</em> and <em>Questions to Attempt</em> settings.</li>
    <li>Imported questions are <strong>appended</strong> to the existing bank — they don't replace.</li>
    <li>Choices are shuffled per student at attempt time (coming in 1B.2).</li>
  </ul>
</div>

<div class="imp-card">
  <h3>Upload CSV</h3>
  <form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="file" name="csv_file" accept=".csv,text/csv" required class="file-input">
    <div style="margin-top:14px">
      <button type="submit" style="background:#1a5c38;color:#fff;border:none;padding:11px 22px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">Import Questions</button>
      <a href="{% url 'lecturers:quiz_detail' quiz.pk %}" style="margin-left:8px;color:#6b7280;text-decoration:none">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
'''


# ========== quiz_form.html: ADD questions_to_attempt RENDER ==========
def patch_quiz_form_template(c):
    if 'questions_to_attempt' in c:
        return None, 'already shows questions_to_attempt'
    anchor = '<div class="g"><label>Time Limit (minutes)</label>{{ form.time_limit_minutes }}'
    if anchor not in c:
        return None, 'could not locate Time Limit anchor in quiz_form.html'
    insertion = '<div class="g"><label>Questions to Attempt</label>{{ form.questions_to_attempt }}<div class="h">{{ form.questions_to_attempt.help_text }}</div></div>\n    '
    return c.replace(anchor, insertion + anchor, 1), 'added Questions-to-Attempt field render'


# ========== quiz_detail.html: ADD Import CSV button + settings entry ==========
def patch_quiz_detail_template(c):
    changed = False
    notes = []
    # 1) Add Import CSV button before "Edit settings"
    if 'quiz_import' not in c:
        anchor = '<a href="{% url \'lecturers:quiz_update\' quiz.pk %}"'
        if anchor in c:
            btn = ('<a href="{% url \'lecturers:quiz_import\' quiz.pk %}" '
                   'style="background:#fff;color:#1a5c38;border:1px solid #bbf7d0;'
                   'padding:8px 14px;border-radius:8px;font-size:12px;'
                   'text-decoration:none;font-weight:500">Import CSV</a>\n    ')
            c = c.replace(anchor, btn + anchor, 1)
            changed = True
            notes.append('added Import CSV button')
        else:
            notes.append('Import CSV button: anchor not found')
    else:
        notes.append('Import CSV button: already present')
    # 2) Add "To Attempt" cell in settings grid before "Questions" cell
    if '>To Attempt<' not in c:
        anchor = '<div><label>Questions</label><div>{{ quiz.question_count }}'
        if anchor in c:
            cell = ('<div><label>To Attempt</label><div>'
                    '{% if quiz.questions_to_attempt %}{{ quiz.questions_to_attempt }} of {{ quiz.question_count }} random'
                    '{% else %}All ({{ quiz.question_count }}){% endif %}</div></div>\n    ')
            c = c.replace(anchor, cell + anchor, 1)
            changed = True
            notes.append('added "To Attempt" settings cell')
        else:
            notes.append('"To Attempt" cell: anchor not found')
    else:
        notes.append('"To Attempt" cell: already present')
    return (c if changed else None), '; '.join(notes)


# ========== APPLY ==========

def patch_file(path, label, fn):
    if not path.exists():
        print(f'  ✗ {label}: not found'); return
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


print('\n=== Phase 1B.1c patcher ===\n')

print('[1/6] lecturers/models.py (add questions_to_attempt):')
patch_file(ROOT / 'lecturers/models.py', 'Quiz model', patch_model)

print('\n[2/6] lecturers/forms.py (add field to QuizForm):')
patch_file(ROOT / 'lecturers/forms.py', 'QuizForm', patch_form)

print('\n[3/6] lecturers/views.py (append quiz_import_csv):')
def p_views(c):
    if 'def quiz_import_csv(' in c:
        return None, 'quiz_import_csv already present'
    return c.rstrip() + VIEWS_ADDITION + '\n', 'appended quiz_import_csv view'
patch_file(ROOT / 'lecturers/views.py', 'views.py', p_views)

print('\n[4/6] lecturers/urls.py (add quiz_import URL):')
def p_urls(c):
    if "name='quiz_import'" in c:
        return None, 'quiz_import URL already present'
    m = re.search(r"(path\('quizzes/<int:pk>/edit/.*?\n)", c)
    if not m:
        return None, 'could not find quiz_update path anchor'
    return c[:m.end()] + URL_LINE + c[m.end():], 'inserted quiz_import URL after quiz_update'
patch_file(ROOT / 'lecturers/urls.py', 'urls.py', p_urls)

print('\n[5/6] quiz_import.html (new template):')
write_template(ROOT / 'lecturers/templates/lecturers/quiz_import.html', QUIZ_IMPORT_HTML, 'quiz_import.html')

print('\n[6/6] update quiz_form.html and quiz_detail.html:')
patch_file(ROOT / 'lecturers/templates/lecturers/quiz_form.html',   'quiz_form.html',   patch_quiz_form_template)
patch_file(ROOT / 'lecturers/templates/lecturers/quiz_detail.html', 'quiz_detail.html', patch_quiz_detail_template)

print('\n=== DONE ===')
print('\nNow run:')
print('  python manage.py makemigrations lecturers')
print('  python manage.py migrate')
print('  python manage.py check')
print('  touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')