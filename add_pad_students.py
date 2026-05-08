import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmt_portal.settings')
django.setup()

from accounts.models import User
from students.models import Student
from academics.models import Programme
from core.models import Session, Semester

session  = Session.objects.filter(is_active=True).first()
semester = Semester.objects.filter(is_active=True).first()

if not session or not semester:
    print("ERROR: No active session/semester."); exit()

pad2 = Programme.objects.filter(code='PAD', level='diploma2').first()
if not pad2:
    pad2 = Programme.objects.filter(name__icontains='Public Admin', level='diploma2').first()

print(f"Session: {session} | Semester: {semester}")
print(f"Programme: {pad2}")
print("-" * 60)

STUDENTS = [
    ('SHEHU SADE',                          'DPL/PAD/24/152'),
    ('LUBABATU ABDULKARIM',                 'DPL/PAD/24/153'),
    ('AHMAD AHMAD',                         'DPL/PAD/24/154'),
    ('SULAIMAN ABDULLAHI',                  'DPL/PAD/24/155'),
    ('IBRAHIM SHEHU',                       'DPL/PAD/24/156'),
    ('MUJITTAPHA SANUSI',                   'DPL/PAD/24/157'),
    ('ABDULMALIK LAWAL',                    'DPL/PAD/24/158'),
    ('MUDANSIR ABDULRAHMAN',                'DPL/PAD/24/159'),
    ('ABBA BALA',                           'DPL/PAD/24/160'),
    ('JIBRIN ZAYYANA',                      'DPL/PAD/24/161'),
    # DPL/PAD/24/162 SAMINU HAMBALI     — NO MATRIC, SKIPPED
    # DPL/PAD/24/163 BILYAMINU IBRAHIM  — NO MATRIC, SKIPPED
    ('BISHIR UMAR SALLAMA',                 'DPL/PAD/24/166'),
    ('MUSA MUSBAHU',                        'DPL/PAD/24/169'),
    ('ABDULAZIZ AHMED',                     'DPL/PAD/24/170'),
    ('SULAIMAN SALMANU',                    'DPL/PAD/24/171'),
    ('UMAR ABDULLAHI',                      'DPL/PAD/24/172'),
    ('HAUWAU ABUBAKAR',                     'DPL/PAD/24/173'),
    ('HALIMATU ABDULLAHI',                  'DPL/PAD/24/174'),
    ('UMAR SHUAIBU',                        'DPL/PAD/24/175'),
    ('ABUBAKAR TUKUR',                      'DPL/PAD/24/176'),
    ('MUHAMMAD A MUHAMMAD',                 'DPL/PAD/24/177'),
    ('AMINU ABDULRAZAK',                    'DPL/PAD/24/178'),
    ('SAUDAT SALISU SHARIF',                'DPL/PAD/24/179'),
    ('AISHA AMINU',                         'DPL/PAD/24/180'),
    ('HADIZA AMINU',                        'DPL/PAD/24/181'),
    ('NAFISA ILIYASU USMAN',                'DPL/PAD/24/182'),
    ('SANI ABDULLAHI',                      'DPL/PAD/24/183'),
    ('MUJITAPHA ABDULLAHI',                 'DPL/PAD/24/184'),
    ('ABUBAKAR BISHIR',                     'DPL/PAD/24/185'),
    ('AMINU SALISU',                        'DPL/PAD/24/186'),
    ('HAYATU AMINU',                        'DPL/PAD/24/187'),
    ('ABBA ABDULLAHI',                      'DPL/PAD/24/188'),
    ('HALILU ABUBAKAR',                     'DPL/PAD/24/189'),
    ('KABIR ABDULLAHI',                     'DPL/PAD/24/190'),
    ('IBRAHIM ALI BABBA',                   'DPL/PAD/24/191'),
    ('SALISU ALIYU MUHAMMAD',               'DPL/PAD/24/192'),
    ('HALIMA HAMZA',                        'DPL/PAD/24/193'),
    ('ZAINAB GARBA',                        'DPL/PAD/24/194'),
    ('ABDULLAHI ABUBAKAR',                  'DPL/PAD/24/195'),
    ('IBRAHIM ABDULLAHI',                   'DPL/PAD/24/196'),
    ('SHAMSU SULEIMAN',                     'DPL/PAD/24/197'),
    ('AWAISU ILIYASU',                      'DPL/PAD/24/198'),
    ('SAIFULLAHI ALIYU',                    'DPL/PAD/24/199'),
    ('SHAMSUDDEEN YAHAYA',                  'DPL/PAD/24/200'),
    ('USMAN UMAR',                          'DPL/PAD/24/201'),
    ('MUHAMMAD ABDULHAMID ABDULRAHMAN',     'DPL/PAD/24/202'),
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
            programme=pad2,
            current_session=session,
            current_semester=semester,
            status='active',
        )
        print(f"  OK    {reg} — {name}")
        created += 1
    except Exception as e:
        print(f"  ERROR {reg} — {name}: {e}")
        errors += 1

print("-" * 60)
print(f"DONE: {created} created | {skipped} skipped | {errors} errors")
print(f"Total students in DB: {Student.objects.count()}")
print()
print("2 students skipped (no matric number):")
print("  - SAMINU HAMBALI")
print("  - BILYAMINU IBRAHIM")
print("Add them manually when their matric numbers are available.")
