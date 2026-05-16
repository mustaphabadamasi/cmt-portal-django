#!/usr/bin/env python3
"""Remove the 'Create Quizzes' card from What's Coming (it's now built)."""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

p = ROOT / 'lecturers/templates/lecturers/lecturer_dashboard.html'
if not p.exists():
    sys.exit('lecturer_dashboard.html not found')

c = p.read_text(encoding='utf-8')

# Matches the exact 4-div card structure for "Create Quizzes"
pat = re.compile(
    r'\n\s*<div\s+style="padding:14px;border:1px solid #e5e7eb;border-radius:10px;opacity:\.65"\s*>'
    r'\s*<div[^>]*>[^<]*</div>'
    r'\s*<div[^>]*>Create Quizzes</div>'
    r'\s*<div[^>]*>[^<]*</div>'
    r'\s*</div>'
)

m = pat.search(c)
if not m:
    print("  • 'Create Quizzes' card not found (already removed?)")
else:
    p.write_text(c[:m.start()] + c[m.end():], encoding='utf-8')
    print("  ✓ Removed 'Create Quizzes' card from What's Coming")

print('\nReload: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')