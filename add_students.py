import os, django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmt_portal.settings')
django.setup()

from accounts.models import User
from students.models import Student
from academics.models import Programme
from core.models import Session, Semester

# 1. Get active session and semester
session = Session.objects.filter(is_active=True).first()
semester = Semester.objects.filter(is_active=True).first()

if not session:
    print("ERROR: No active session found. Please create/activate one in admin.")
    exit()
if not semester:
    print("ERROR: No active semester found. Please create/activate one in admin.")
    exit()

print(f"Using session: {session} | Using semester: {semester}")
print("-" * 60)

# 2. Student Data List
STUDENTS_DATA = [
    # ── DIPLOMA IN BUSINESS ADMINISTRATION ──────────────────
    {'name': 'Aminu Abdullahi',        'reg': 'DPL/BUS/23/034', 'code': 'BUS'},
    {'name': 'Khadija Mukhtar',        'reg': 'DPL/BUS/23/035', 'code': 'BUS'},
    {'name': 'Bala Sani',              'reg': 'DPL/BUS/23/036', 'code': 'BUS'},
    {'name': 'Aliyu Maikudi',          'reg': 'DPL/BUS/23/037', 'code': 'BUS'},
    {'name': 'Abdulwahab Abdullahi',   'reg': 'DPL/BUS/23/038', 'code': 'BUS'},
    {'name': 'Umar Abdullahi Sani',    'reg': 'DPL/BUS/23/039', 'code': 'BUS'},
    {'name': 'Ibrahim Dahiru Ahmad',   'reg': 'DPL/BUS/23/040', 'code': 'BUS'},
    {'name': 'Shuaibu Aminu',          'reg': 'DPL/BUS/23/041', 'code': 'BUS'},
    {'name': 'Martha Joel Dauda',      'reg': 'DPL/BUS/23/042', 'code': 'BUS'},
    {'name': 'Muhammadu Balarabe Aliyu','reg': 'DPL/BUS/23/043', 'code': 'BUS'},
    {'name': 'Rukayya Bishir',          'reg': 'DPL/BUS/23/044', 'code': 'BUS'},

    # ── DIPLOMA IN PUBLIC ADMINISTRATION ────────────────────
    {'name': 'Amina Musa',              'reg': 'DPL/PAD/23/128', 'code': 'PAD'},
    {'name': 'Sagir Lawal',             'reg': 'DPL/PAD/23/129', 'code': 'PAD'},
    {'name': 'Ibrahim Aliyu',           'reg': 'DPL/PAD/23/130', 'code': 'PAD'},
    {'name': 'Usman Ibrahim',           'reg': 'DPL/PAD/23/131', 'code': 'PAD'},
    {'name': 'Fatima Aminu Wali',       'reg': 'DPL/PAD/23/132', 'code': 'PAD'},
    {'name': 'Ahmad Dahiru',            'reg': 'DPL/PAD/23/133', 'code': 'PAD'},
    {'name': 'Rabiu Abdulrahman',       'reg': 'DPL/PAD/23/134', 'code': 'PAD'},
    {'name': 'Deborah Dauda',           'reg': 'DPL/PAD/23/135', 'code': 'PAD'},
    {'name': 'Suleiman Yahaya',         'reg': 'DPL/PAD/23/136', 'code': 'PAD'},
    {'name': 'Zainab Zayyana',          'reg': 'DPL/PAD/23/137', 'code': 'PAD'},
    {'name': 'Jamilu Usman',            'reg': 'DPL/PAD/23/140', 'code': 'PAD'},
    {'name': 'Ahmodu Sule Emmanuel',    'reg': 'DPL/PAD/23/141', 'code': 'PAD'},
    {'name': 'Rabiu Zaharaddeen',       'reg': 'DPL/PAD/23/142', 'code': 'PAD'},
    {'name': 'Hassan Sani',             'reg': 'DPL/PAD/23/143', 'code': 'PAD'},
    {'name': 'Zayyana Sale',            'reg': 'DPL/PAD/23/144', 'code': 'PAD'},
    {'name': 'Muhammad Yahaya',         'reg': 'DPL/PAD/23/145', 'code': 'PAD'},
    {'name': 'Rukayya Aminu',           'reg': 'DPL/PAD/23/147', 'code': 'PAD'},
    {'name': 'Hussaini Abdulsalam Salihu', 'reg': 'DPL/PAD/23/149', 'code': 'PAD'},
    {'name': 'Sagir Umar',              'reg': 'DPL/PAD/23/150', 'code': 'PAD'},
    {'name': 'Zaharaddini Gide',        'reg': 'DPL/PAD/23/151', 'code': 'PAD'},
]

created = skipped = errors = 0

for s in STUDENTS_DATA:
    # A. Determine Level based on Matric Year
    # /25/ is Diploma 1, /24/ and /23/ are Diploma 2 (Promoted students)
    target_level = 'diploma1' if '/25/' in s['reg'] else 'diploma2'

    # B. Resolve Programme (Fixes the MultipleObjectsReturned error)
    try:
        prog = Programme.objects.get(code=s['code'], level=target_level)
    except Programme.DoesNotExist:
        print(f"  SKIP  {s['reg']} — {s['name']} (Prog {s['code']} {target_level} not found)")
        skipped += 1
        continue

    # C. Check if User already exists
    if User.objects.filter(username=s['reg']).exists():
        print(f"  SKIP  {s['reg']} — {s['name']} (Already exists)")
        skipped += 1
        continue

    # D. Create User and Student profile
    # Inside your loop in add_students.py
try:
    with transaction.atomic():
        user = User.objects.create_user(
            username=s['reg'],
            password=s['reg'],
            first_name=first,
            last_name=last,
            role='student'
        )
        user.save() # Explicitly call save

        student = Student.objects.create(
            user=user,
            reg_number=s['reg'],
            programme=prog,
            current_session=session,
            current_semester=semester,
            status='active'
        )
        print(f"Successfully SAVED: {s['reg']}")
        created += 1
except Exception as e:
    print(f"FAILED to save {s['reg']}: {e}")