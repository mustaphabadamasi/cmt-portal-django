#!/usr/bin/env python3
"""Make results permission helpers related_name-agnostic."""
import pathlib, sys

ROOT = pathlib.Path('.').resolve()
if not (ROOT / 'manage.py').exists():
    sys.exit('Run from project root')

p = ROOT / 'lecturers/views.py'
c = p.read_text(encoding='utf-8')
changes = []

# 1) _can_view_results — replace ownership check
old1 = """    if getattr(user, 'role', None) == 'lecturer' and hasattr(user, 'lecturer'):
        return quiz.created_by_id == user.lecturer.id
    return False"""
new1 = """    if getattr(user, 'role', None) == 'lecturer':
        return bool(quiz.created_by) and quiz.created_by.user_id == user.id
    return False"""
if old1 in c:
    c = c.replace(old1, new1, 1)
    changes.append('_can_view_results')

# 2) _can_view_course_results — replace lecturer lookup
old2 = """    if getattr(user, 'role', None) == 'lecturer' and hasattr(user, 'lecturer'):
        return LecturerCourse.objects.filter(
            lecturer=user.lecturer, course=course, semester=semester, is_active=True
        ).exists()
    return False"""
new2 = """    if getattr(user, 'role', None) == 'lecturer':
        return LecturerCourse.objects.filter(
            lecturer__user=user, course=course, semester=semester, is_active=True
        ).exists()
    return False"""
if old2 in c:
    c = c.replace(old2, new2, 1)
    changes.append('_can_view_course_results')

# 3) Dashboard quiz_count — same fix (in case dashboard patcher already ran)
old3 = "Quiz.objects.filter(created_by=request.user.lecturer).count()"
new3 = "Quiz.objects.filter(created_by__user=request.user).count()"
if old3 in c:
    c = c.replace(old3, new3)
    changes.append('dashboard quiz_count query')

if changes:
    p.write_text(c, encoding='utf-8')
    print('Patched:')
    for ch in changes:
        print(f'  ✓ {ch}')
else:
    print('• No changes needed (already patched or text not found)')

print('\nReload: touch /var/www/mustapher001_pythonanywhere_com_wsgi.py')