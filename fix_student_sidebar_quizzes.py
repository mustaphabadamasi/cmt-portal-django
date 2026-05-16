#!/usr/bin/env python3
"""Insert 'Available Quizzes' into every inlined student sidebar by cloning the Exam Card link."""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

STUDENTS_DIR = ROOT / 'templates' / 'students'
if not STUDENTS_DIR.exists():
    sys.exit('templates/students/ not found')

NEW_HREF = "{% url 'lecturers:student_quiz_list' %}"
NEW_TEXT = 'Available Quizzes'
ANCHORS  = ['Exam Card', 'Print Course Form', 'My Courses']  # try in this order

patched, skipped, no_sidebar = 0, 0, 0

for path in sorted(STUDENTS_DIR.glob('*.html')):
    txt = path.read_text(encoding='utf-8')
    if NEW_TEXT in txt:
        print(f'  • {path.name}: already patched')
        skipped += 1
        continue

    found = None
    for label in ANCHORS:
        if label in txt:
            pat = r'<a\b[^>]*>[\s\S]*?' + re.escape(label) + r'[\s\S]*?</a>'
            m = re.search(pat, txt)
            if m:
                found = (label, m)
                break

    if found is None:
        no_sidebar += 1
        continue

    label, m = found
    cloned = m.group(0)
    # Replace href value with the quiz URL
    cloned = re.sub(r'href="[^"]*"', f'href="{NEW_HREF}"', cloned, count=1)
    # Swap the link text
    cloned = cloned.replace(label, NEW_TEXT)
    # Swap the first Bootstrap icon class (if any) for a quiz-style icon
    cloned = re.sub(r'\bbi-[a-z0-9-]+\b', 'bi-patch-question', cloned, count=1)
    # Strip any "active" so the new link isn't pre-highlighted
    cloned = re.sub(
        r"\{%\s*if\s+request\.resolver_match\.url_name\s*==\s*'[^']+'\s*%\}\s*active\s*\{%\s*endif\s*%\}",
        "",
        cloned,
    )
    cloned = re.sub(r'\s+\bactive\b', '', cloned)

    new_txt = txt[:m.end()] + '\n        ' + cloned + txt[m.end():]
    path.write_text(new_txt, encoding='utf-8')
    print(f'  ✓ {path.name}: inserted after "{label}"')
    patched += 1

print()
print(f'Patched: {patched} | Already had link: {skipped} | No sidebar found: {no_sidebar}')
print('\nNow run: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')