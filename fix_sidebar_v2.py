#!/usr/bin/env python3
"""
Undo the v1 sidebar duplication bug and properly insert a single
'Available Quizzes' link after each Exam Card link.
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

STUDENTS_DIR = ROOT / 'templates' / 'students'

NEW_HREF = "{% url 'lecturers:student_quiz_list' %}"
NEW_TEXT = 'Available Quizzes'

# Matches a CORRUPTED multi-anchor block: starts with <a href="{quiz_url}",
# spans at least one inner </a> (proving it's multi-anchor), through the
# closing </a> of the 'Available Quizzes' anchor.
corrupt_pat = re.compile(
    r'\n\s*<a\b[^>]*href="\{%\s*url\s+\'lecturers:student_quiz_list\'\s*%\}"'
    r'[\s\S]*?</a>[\s\S]*?Available Quizzes[\s\S]*?</a>'
)

# Single-anchor matcher — uses negative lookahead so it CANNOT cross </a>
exam_pat = re.compile(
    r'<a\b(?:(?!</a>)[\s\S])*?Exam Card(?:(?!</a>)[\s\S])*?</a>'
)

cleaned = 0
inserted = 0
already_ok = 0
no_anchor = 0

for path in sorted(STUDENTS_DIR.glob('*.html')):
    txt = path.read_text(encoding='utf-8')
    actions = []

    # --- Step 1: remove any corrupted duplicated blocks ---
    new_txt, n = corrupt_pat.subn('', txt)
    if n > 0:
        actions.append(f'removed {n} corrupted block(s)')
        txt = new_txt
        cleaned += n

    # --- Step 2: did the file already end up with a clean Available Quizzes? ---
    if NEW_TEXT in txt:
        if actions:
            path.write_text(txt, encoding='utf-8')
            print(f'  ✓ {path.name}: {"; ".join(actions)} (already had clean link)')
            already_ok += 1
        else:
            print(f'  • {path.name}: already clean')
            already_ok += 1
        continue

    # --- Step 3: properly insert a single Exam-Card-style clone ---
    m = exam_pat.search(txt)
    if not m:
        if actions:
            path.write_text(txt, encoding='utf-8')
            print(f'  ⚠ {path.name}: cleaned but no Exam Card found to anchor on')
            no_anchor += 1
        continue

    cloned = m.group(0)
    cloned = re.sub(r'href="[^"]*"', f'href="{NEW_HREF}"', cloned, count=1)
    cloned = cloned.replace('Exam Card', NEW_TEXT)
    cloned = re.sub(r'\bbi-[a-z0-9-]+\b', 'bi-patch-question', cloned, count=1)
    cloned = re.sub(
        r"\{%\s*if\s+request\.resolver_match\.url_name\s*==\s*'[^']+'\s*%\}\s*active\s*\{%\s*endif\s*%\}",
        "",
        cloned,
    )
    cloned = re.sub(r'\s+\bactive\b', '', cloned)

    new_txt = txt[:m.end()] + '\n        ' + cloned + txt[m.end():]
    path.write_text(new_txt, encoding='utf-8')
    actions.append('inserted single Available Quizzes link')
    print(f'  ✓ {path.name}: {"; ".join(actions)}')
    inserted += 1

print()
print(f'Cleanup removals: {cleaned}')
print(f'New insertions:   {inserted}')
print(f'Already-clean:    {already_ok}')
print(f'No anchor found:  {no_anchor}')
print('\nReload: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')