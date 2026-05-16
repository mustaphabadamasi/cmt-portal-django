#!/usr/bin/env python3
"""Add 'Lecturer Management' card to registrar dashboard
and 'Lecturers' entry to registrar sidebar. Idempotent."""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

# ---------- Dashboard card ----------
LECTURER_CARD = '''
  <a href="{% url 'lecturers:list' %}" class="ql">
    <div class="ql-icon">🎓</div><div class="ql-title">Lecturer Management</div><div class="ql-sub">Add lecturers & assign courses</div>
  </a>'''

dash = ROOT / 'templates/registrar/dashboard.html'
if dash.exists():
    s = dash.read_text(encoding='utf-8')
    if 'Lecturer Management' in s:
        print('• dashboard.html: Lecturer Management card already present')
    else:
        # Insert after the Student Records card
        pat = r"(<a\s+href=\"\{%\s*url\s+'registrar_students'\s*%\}\"\s+class=\"ql\">.*?</a>)"
        m = re.search(pat, s, flags=re.DOTALL)
        if m:
            dash.write_text(s[:m.end()] + LECTURER_CARD + s[m.end():], encoding='utf-8')
            print('✓ dashboard.html: added Lecturer Management card after Student Records')
        else:
            print("✗ dashboard.html: couldn't find Student Records card — patch by hand")
else:
    print('✗ templates/registrar/dashboard.html not found')

# ---------- Sidebar entry ----------
LECTURER_NAV = "    <a href=\"{% url 'lecturers:list' %}\" class=\"nav-item {% if request.resolver_match.namespace == 'lecturers' %}active{% endif %}\"><span class=\"ico\">🎓</span> Lecturers</a>\n"

base = ROOT / 'templates/registrar/base.html'
if base.exists():
    s = base.read_text(encoding='utf-8')
    if "lecturers:list" in s:
        print('• registrar/base.html: Lecturers sidebar entry already present')
    else:
        # Insert right after the Course Outlines line
        pat = r"(<a\s+href=\"\{%\s*url\s+'course_structure'\s*%\}\".*?</a>\s*\n)"
        m = re.search(pat, s)
        if m:
            base.write_text(s[:m.end()] + LECTURER_NAV + s[m.end():], encoding='utf-8')
            print('✓ registrar/base.html: added Lecturers entry under Academic section')
        else:
            print("✗ registrar/base.html: couldn't find Course Outlines link — patch by hand")
else:
    print('✗ templates/registrar/base.html not found')

print('\nNow run: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')