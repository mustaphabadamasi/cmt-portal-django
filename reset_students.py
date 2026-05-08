import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmt_portal.settings')
django.setup()

from accounts.models import User
from students.models import Student
from academics.models import Programme
from core.models import Session, Semester

# ── STEP 1: Remove all /23/ students ────────────────────────
old = Student.objects.filter(reg_number__contains='/23/')
count = old.count()
for s in old:
    s.user.delete()  # deletes user + student via cascade
print(f"Deleted {count} students with /23/ reg numbers.")

# ── STEP 2: Add new /24/ students ───────────────────────────
session  = Session.objects.filter(is_active=True).first()
semester = Semester.objects.filter(is_active=True).first()

if not session:
    print("ERROR: No active session."); exit()
if not semester:
    print("ERROR: No active semester."); exit()

print(f"Session: {session} | Semester: {semester}")

bus2 = Programme.objects.filter(code='BUS', level='diploma2').first()
if not bus2:
    bus2 = Programme.objects.filter(name__icontains='Business', level='diploma2').first()
print(f"Programme: {bus2}")
print("-" * 55)

STUDENTS = [
    ('FATIMA HUSSAINI',            'DPL/BUS/24/047'),
    ('ABBA MUHAMMAD ABUBAKAR',     'DPL/BUS/24/048'),
    ('SAFIYYA SANI',               'DPL/BUS/24/049'),
    ('MAIMUNATU ABUBAKAR',         'DPL/BUS/24/050'),
    ('AMINU LURWANU',              'DPL/BUS/24/051'),
    ('MUKHTAR ABDULKADIR',         'DPL/BUS/24/052'),
    ('USMAN SANI',                 'DPL/BUS/24/053'),
    ('MIRACLE AGBORZEGBE AZONIM',  'DPL/BUS/24/054'),
    ('ABDULLAHI BISHIR',           'DPL/BUS/24/055'),
    ('AMINA HASSAN BABBA',         'DPL/BUS/24/056'),
    ('MUHAMMAD AL AMEEN',          'DPL/BUS/24/057'),
    ('ABDULKADIR SAIDU',           'DPL/BUS/24/058'),
    ('ABUBAKAR KASIMU',            'DPL/BUS/24/059'),
    ('IMAM HASSAN AMINU',          'DPL/BUS/24/060'),
    ('IBRAHIM ISYAKU IBRAHIM',     'DPL/BUS/24/061'),
    ('KHADIJA AHMED',              'DPL/BUS/24/062'),
    ('ABUBAKAR AHMAD',             'DPL/BUS/24/063'),
    ('NIIMATU MUSA USMAN',         'DPL/BUS/24/064'),
    ('ABUSUFIYANU MUSA',           'DPL/BUS/24/065'),
    ('IBRAHIM ISYAKU DARMA',       'DPL/BUS/24/066'),
    ('HADIZA IBRAHIM DUWANA',      'DPL/BUS/24/067'),
]

created = skipped = errors = 0

for name, reg in STUDENTS:
    if User.objects.filter(username=reg).exists():
        print(f"  SKIP  {reg} — {name} (already exists)")
        skipped += 1
        continue
    try:
        parts = name.title().split(' ', 1)
        first = parts[0]
        last  = parts[1] if len(parts) > 1 else ''
        user = User.objects.create_user(
            username=reg,
            password=reg,
            first_name=first,
            last_name=last,
            role='student',
            must_change_password=True,
        )
        Student.objects.create(
            user=user,
            reg_number=reg,
            programme=bus2,
            current_session=session,
            current_semester=semester,
            status='active',
        )
        print(f"  OK    {reg} — {name}")
        created += 1
    except Exception as e:
        print(f"  ERROR {reg} — {name}: {e}")
        errors += 1

print("-" * 55)
print(f"DONE: {created} created | {skipped} skipped | {errors} errors")
print(f"Total students in DB: {Student.objects.count()}")
print()
print("Students login with:")
print("  Username = reg number  e.g.  DPL/BUS/24/047")
print("  Password = reg number  (same)")
print("  They will be prompted to change password on first login.")
