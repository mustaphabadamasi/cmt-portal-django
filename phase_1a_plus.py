#!/usr/bin/env python3
"""
Phase 1A+ patcher — creates lecturer dashboard + my_courses, wires login
dispatch, adds lecturer sidebar branch. Idempotent.

Run from project root:
    cd ~/cmt-portal-django && python3 phase_1a_plus.py
"""
import pathlib, re, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit(f'Run me from the Django project root (no manage.py in {ROOT})')


# =====================================================================
# 1. NEW TEMPLATE FILES
# =====================================================================
LECTURER_DASHBOARD_HTML = r'''{% extends "base.html" %}
{% block page_title %}Dashboard{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">Welcome, {{ lecturer.title }} {{ lecturer.user.first_name }}</div>
    <div class="page-sub">{{ lecturer.staff_id }} · {{ lecturer.department|default:"Academic Staff" }}</div>
  </div>
</div>

<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:24px">
  <div class="stat-card green">
    <div class="stat-icon green"><i class="bi bi-book-half"></i></div>
    <div class="stat-value">{{ active_courses_count }}</div>
    <div class="stat-label">Active Courses</div>
  </div>
  <div class="stat-card blue">
    <div class="stat-icon blue"><i class="bi bi-patch-question"></i></div>
    <div class="stat-value">—</div>
    <div class="stat-label">Quizzes (coming)</div>
  </div>
  <div class="stat-card amber">
    <div class="stat-icon amber"><i class="bi bi-journal-text"></i></div>
    <div class="stat-value">—</div>
    <div class="stat-label">Assignments (coming)</div>
  </div>
  <div class="stat-card">
    <div class="stat-icon green"><i class="bi bi-chat-square-text"></i></div>
    <div class="stat-value">—</div>
    <div class="stat-label">Forum Posts (coming)</div>
  </div>
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:20px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;margin:0">My Active Courses</h3>
    <a href="{% url 'lecturers:my_courses' %}" style="font-size:12px;color:#1a5c38;text-decoration:none;font-weight:600">View all →</a>
  </div>
  {% if by_semester %}
    {% for semester, items in by_semester.items %}
      <div style="margin-bottom:18px">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#6b7280;font-weight:700;margin-bottom:8px">{{ semester }}</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px">
          {% for a in items %}
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px">
              <div style="font-weight:700;color:#111;font-size:14px">{{ a.course.code }}</div>
              <div style="color:#374151;font-size:13px;margin-top:2px">{{ a.course.title }}</div>
              <div style="color:#6b7280;font-size:11px;margin-top:6px">{{ a.course.programme }} · {{ a.course.unit }} unit{{ a.course.unit|pluralize }}</div>
            </div>
          {% endfor %}
        </div>
      </div>
    {% endfor %}
  {% else %}
    <div style="text-align:center;padding:36px 16px;color:#9ca3af">
      <i class="bi bi-book" style="font-size:42px;display:block;margin-bottom:8px"></i>
      No courses assigned yet. Contact the Registrar or Academic Secretary to be assigned.
    </div>
  {% endif %}
</div>

<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px">
  <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;margin:0 0 14px">What's Coming</h3>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px">
    <div style="padding:14px;border:1px solid #e5e7eb;border-radius:10px;opacity:.65">
      <div style="font-size:22px;margin-bottom:6px">📝</div>
      <div style="font-weight:600;font-size:13px">Create Quizzes</div>
      <div style="font-size:11px;color:#6b7280;margin-top:3px">MCQ quizzes worth 20 marks, gated by course registration.</div>
    </div>
    <div style="padding:14px;border:1px solid #e5e7eb;border-radius:10px;opacity:.65">
      <div style="font-size:22px;margin-bottom:6px">📋</div>
      <div style="font-weight:600;font-size:13px">Set Assignments</div>
      <div style="font-size:11px;color:#6b7280;margin-top:3px">Individual & group assignments, 10 marks each.</div>
    </div>
    <div style="padding:14px;border:1px solid #e5e7eb;border-radius:10px;opacity:.65">
      <div style="font-size:22px;margin-bottom:6px">💬</div>
      <div style="font-weight:600;font-size:13px">Course Forum</div>
      <div style="font-size:11px;color:#6b7280;margin-top:3px">Per-course discussion board with your students.</div>
    </div>
    <div style="padding:14px;border:1px solid #e5e7eb;border-radius:10px;opacity:.65">
      <div style="font-size:22px;margin-bottom:6px">🎥</div>
      <div style="font-weight:600;font-size:13px">Live Classes</div>
      <div style="font-size:11px;color:#6b7280;margin-top:3px">Schedule online sessions with meeting links + attendance.</div>
    </div>
  </div>
</div>
{% endblock %}
'''


MY_COURSES_HTML = r'''{% extends "base.html" %}
{% block page_title %}My Courses{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <div class="page-title">My Courses</div>
    <div class="page-sub">All courses ever assigned to you — {{ assignments|length }} total</div>
  </div>
</div>

<style>
  .courses-table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;font-size:13px}
  .courses-table th{background:#1a5c38;color:#fff;padding:10px 14px;text-align:left;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
  .courses-table td{padding:11px 14px;border-bottom:1px solid #f3f4f6;vertical-align:middle}
  .courses-table tr:hover td{background:#f9fafb}
  .badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600}
  .badge-active{background:#d1fae5;color:#065f46}
  .badge-inactive{background:#e5e7eb;color:#374151}
</style>

<table class="courses-table">
  <thead>
    <tr><th>#</th><th>Course Code</th><th>Title</th><th>Programme</th><th>Unit</th><th>Semester</th><th>Status</th><th>Actions</th></tr>
  </thead>
  <tbody>
    {% for a in assignments %}
      <tr>
        <td>{{ forloop.counter }}</td>
        <td style="font-family:monospace;font-weight:600">{{ a.course.code }}</td>
        <td>{{ a.course.title }}</td>
        <td>{{ a.course.programme }}</td>
        <td>{{ a.course.unit }}</td>
        <td>{{ a.semester }}</td>
        <td>{% if a.is_active %}<span class="badge badge-active">Active</span>{% else %}<span class="badge badge-inactive">Inactive</span>{% endif %}</td>
        <td style="color:#9ca3af;font-size:11px">Quiz · Assignment · Forum <em>(coming)</em></td>
      </tr>
    {% empty %}
      <tr><td colspan="8" style="text-align:center;color:#9ca3af;padding:32px">No course assignments yet.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
'''


VIEWS_ADDITION = '''

# ============================================================
# Lecturer-facing views (lecturer logs in, sees own data)
# ============================================================

def lecturer_required(view_func):
    """Allow only users with role='lecturer' who have a linked Lecturer profile."""
    @login_required
    def wrapper(request, *args, **kwargs):
        u = request.user
        if u.role == 'lecturer' and hasattr(u, 'lecturer_profile'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("This area is for lecturers only.")
    return wrapper


@lecturer_required
def lecturer_dashboard(request):
    lecturer = request.user.lecturer_profile
    active_assignments = (
        lecturer.course_assignments
        .filter(is_active=True)
        .select_related('course', 'course__programme', 'semester', 'semester__session')
        .order_by('-semester__session__name', '-semester__name', 'course__code')
    )
    by_semester = {}
    for a in active_assignments:
        by_semester.setdefault(f"{a.semester}", []).append(a)
    return render(request, 'lecturers/lecturer_dashboard.html', {
        'lecturer': lecturer,
        'by_semester': by_semester,
        'active_courses_count': active_assignments.count(),
    })


@lecturer_required
def my_courses(request):
    lecturer = request.user.lecturer_profile
    assignments = (
        lecturer.course_assignments
        .select_related('course', 'course__programme', 'semester', 'semester__session')
        .order_by('-is_active', '-semester__session__name', '-semester__name', 'course__code')
    )
    return render(request, 'lecturers/my_courses.html', {
        'lecturer': lecturer,
        'assignments': assignments,
    })
'''


NEW_DASHBOARD = '''@login_required
def dashboard(request):
    user = request.user
    if hasattr(user, 'must_change_password') and user.must_change_password:
        return redirect('change_password')

    role = getattr(user, 'role', 'admin')

    if role == 'student':
        return redirect('student_dashboard')
    elif role == 'lecturer':
        return redirect('lecturers:dashboard')
    elif role == 'registrar':
        return redirect('registrar_dashboard')
    elif role == 'bursar':
        return redirect('admin:index')
    elif role in ['admin', 'academic_officer']:
        return redirect('admin:index')
    return redirect('admin:index')
'''


LECTURER_SIDEBAR = r'''  {% elif user.role == 'lecturer' %}
  <div class="nav-section">Main Menu</div>
  <a href="{% url 'lecturers:dashboard' %}" class="nav-item {% if request.resolver_match.url_name == 'dashboard' and request.resolver_match.namespace == 'lecturers' %}active{% endif %}"><div class="nav-icon"><i class="bi bi-speedometer2"></i></div>Dashboard</a>

  <div class="nav-section">Academic</div>
  <a href="{% url 'lecturers:my_courses' %}" class="nav-item {% if request.resolver_match.url_name == 'my_courses' %}active{% endif %}"><div class="nav-icon"><i class="bi bi-book-half"></i></div>My Courses</a>

  <div class="nav-section">Coming Soon</div>
  <a href="#" class="nav-item" style="opacity:.4;cursor:not-allowed" onclick="return false"><div class="nav-icon"><i class="bi bi-patch-question"></i></div>My Quizzes <span style="margin-left:auto;background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:99px;font-size:9px;font-weight:700">SOON</span></a>
  <a href="#" class="nav-item" style="opacity:.4;cursor:not-allowed" onclick="return false"><div class="nav-icon"><i class="bi bi-journal-text"></i></div>My Assignments <span style="margin-left:auto;background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:99px;font-size:9px;font-weight:700">SOON</span></a>
  <a href="#" class="nav-item" style="opacity:.4;cursor:not-allowed" onclick="return false"><div class="nav-icon"><i class="bi bi-chat-square-text"></i></div>Course Forum <span style="margin-left:auto;background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:99px;font-size:9px;font-weight:700">SOON</span></a>
  <a href="#" class="nav-item" style="opacity:.4;cursor:not-allowed" onclick="return false"><div class="nav-icon"><i class="bi bi-camera-video"></i></div>Live Classes <span style="margin-left:auto;background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:99px;font-size:9px;font-weight:700">SOON</span></a>

'''


# =====================================================================
# 2. APPLY PATCHES
# =====================================================================

def write_template(path: pathlib.Path, content: str, label: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'  ✓ wrote {label}: {path.relative_to(ROOT)}')


def patch_file(path: pathlib.Path, label: str, fn):
    """fn(content) -> (new_content_or_None, status_msg)"""
    if not path.exists():
        print(f'  ✗ {label} not found: {path}')
        return
    content = path.read_text(encoding='utf-8')
    new_content, msg = fn(content)
    if new_content is None:
        print(f'  • {label}: {msg}')
    else:
        path.write_text(new_content, encoding='utf-8')
        print(f'  ✓ {label}: {msg}')


print('\n=== Phase 1A+ patcher ===')

# 1. Templates
print('\n[1/5] Writing templates...')
write_template(ROOT / 'lecturers/templates/lecturers/lecturer_dashboard.html',
               LECTURER_DASHBOARD_HTML, 'lecturer dashboard')
write_template(ROOT / 'lecturers/templates/lecturers/my_courses.html',
               MY_COURSES_HTML, 'my courses')

# 2. Append to lecturers/views.py
print('\n[2/5] Updating lecturers/views.py...')
def patch_lecturer_views(content):
    if 'def lecturer_dashboard(' in content:
        return None, 'lecturer_dashboard already present, skipping'
    return content.rstrip() + VIEWS_ADDITION, 'appended lecturer_dashboard + my_courses + lecturer_required'

patch_file(ROOT / 'lecturers/views.py', 'lecturers/views.py', patch_lecturer_views)

# 3. Append to lecturers/urls.py
print('\n[3/5] Updating lecturers/urls.py...')
def patch_lecturer_urls(content):
    if "name='dashboard'" in content:
        return None, "dashboard URL already present, skipping"
    addition = ("    path('dashboard/',  views.lecturer_dashboard, name='dashboard'),\n"
                "    path('my-courses/', views.my_courses,         name='my_courses'),\n")
    # Insert before the closing ']' of urlpatterns
    m = re.search(r'(urlpatterns\s*=\s*\[)(.*?)(\n\])', content, flags=re.DOTALL)
    if not m:
        return None, 'could not locate urlpatterns list — patch by hand'
    new = content[:m.end(2)] + '\n' + addition + content[m.start(3):]
    return new, 'inserted dashboard + my_courses URL patterns'

patch_file(ROOT / 'lecturers/urls.py', 'lecturers/urls.py', patch_lecturer_urls)

# 4. Patch accounts/views.py dashboard()
print('\n[4/5] Updating accounts/views.py dashboard()...')
def patch_accounts_views(content):
    if "redirect('lecturers:dashboard')" in content:
        return None, 'lecturer dispatch already present, skipping'
    # Find the dashboard function and replace it
    pattern = r'@login_required\s*\ndef dashboard\(request\):.*?(?=\n@login_required\b|\n@[a-zA-Z_]|\ndef [a-zA-Z_])'
    m = re.search(pattern, content, flags=re.DOTALL)
    if not m:
        return None, 'could not locate dashboard() — patch by hand'
    return content[:m.start()] + NEW_DASHBOARD + content[m.end():], 'replaced dashboard() with lecturer-aware version'

patch_file(ROOT / 'accounts/views.py', 'accounts/views.py', patch_accounts_views)

# 5. Patch templates/base.html sidebar
print('\n[5/5] Updating templates/base.html sidebar...')
def patch_base_html(content):
    if "user.role == 'lecturer'" in content:
        return None, 'lecturer branch already present, skipping'
    # Insert lecturer block after bursar block ends and before the {% else %} that follows
    pattern = r"(\{%\s*elif\s+user\.role\s*==\s*['\"]bursar['\"]\s*%\}.*?)(\n\s*\{%\s*else\s*%\})"
    m = re.search(pattern, content, flags=re.DOTALL)
    if not m:
        return None, 'could not locate bursar/else block — add the lecturer branch by hand'
    new = content[:m.end(1)] + '\n\n' + LECTURER_SIDEBAR + content[m.start(2):]
    return new, 'inserted lecturer sidebar branch'

patch_file(ROOT / 'templates/base.html', 'templates/base.html', patch_base_html)

print('\n=== DONE ===\n')
print('Now run:')
print('  python manage.py check')
print('  touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')
print('\nThen log out and log in as a lecturer (e.g. sarah@2026 / SPN1002).')