#!/usr/bin/env python3
"""Cleanup pass:
  #1 add Available Quizzes to my_courses.html (anchor on Print Course Form)
  #2 strip the wrongly-inserted link from 6 admin/registrar-side templates
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

STUDENTS = ROOT / 'templates' / 'students'
NEW_HREF = "{% url 'lecturers:student_quiz_list' %}"
NEW_TEXT = 'Available Quizzes'


# === #1 my_courses.html ============================================
def add_to_my_courses(c):
    if NEW_TEXT in c:
        return None, 'my_courses.html: link already present'
    pat = re.compile(r'<a\b(?:(?!</a>)[\s\S])*?Print Course Form(?:(?!</a>)[\s\S])*?</a>')
    m = pat.search(c)
    if not m:
        return None, 'my_courses.html: no Print Course Form anchor'
    cloned = m.group(0)
    cloned = re.sub(r'href="[^"]*"', f'href="{NEW_HREF}"', cloned, count=1)
    cloned = cloned.replace('Print Course Form', NEW_TEXT)
    cloned = re.sub(r'\bbi-[a-z0-9-]+\b', 'bi-patch-question', cloned, count=1)
    cloned = re.sub(
        r"\{%\s*if\s+request\.resolver_match\.url_name\s*==\s*'[^']+'\s*%\}\s*active\s*\{%\s*endif\s*%\}",
        "", cloned,
    )
    cloned = re.sub(r'\s+\bactive\b', '', cloned)
    new = c[:m.end()] + '\n        ' + cloned + c[m.end():]
    return new, 'my_courses.html: inserted Available Quizzes after Print Course Form'


# === #2 strip from admin/registrar templates =======================
ADMIN_FILES = [
    'registrar_dashboard.html',
    'registrar_documents.html',
    'registrar_photo.html',
    'registrar_students.html',
    'student_detail.html',
    'student_list.html',
]

# Single-anchor matcher with negative lookahead so it CANNOT cross </a> boundaries.
STRIP_PAT = re.compile(
    r'\n\s*<a\b(?:(?!</a>)[\s\S])*?lecturers:student_quiz_list(?:(?!</a>)[\s\S])*?</a>'
)


def strip_link(c, fname):
    if NEW_TEXT not in c:
        return None, f'{fname}: no link to strip'
    new, n = STRIP_PAT.subn('', c)
    if n == 0:
        return None, f'{fname}: link present but strip regex did not match (manual check needed)'
    return new, f'{fname}: stripped {n} link(s)'


# === apply =========================================================
def apply(path, label, fn):
    if not path.exists():
        print(f'  ✗ {label}: not found'); return
    c = path.read_text(encoding='utf-8')
    new, msg = fn(c)
    if new is None:
        print(f'  • {msg}')
    else:
        path.write_text(new, encoding='utf-8')
        print(f'  ✓ {msg}')


print('\n=== Cleanup pass ===\n')

print('[#1] my_courses.html — add the link:')
apply(STUDENTS / 'my_courses.html', 'my_courses.html', add_to_my_courses)

print('\n[#2] strip wrongly-inserted link from admin/registrar templates:')
for fname in ADMIN_FILES:
    apply(STUDENTS / fname, fname, lambda c, f=fname: strip_link(c, f))

print('\nDone. Reload: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')