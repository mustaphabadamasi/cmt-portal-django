import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cmt_portal.settings')
django.setup()

from academics.models import Programme, Course

# Get programmes
try:
    PAD = Programme.objects.get(code='PAD', level='diploma1')
    PAD2 = Programme.objects.get(code='PAD', level='diploma2')
except Programme.DoesNotExist:
    PAD = Programme.objects.filter(name__icontains='Public Admin', level='diploma1').first()
    PAD2 = Programme.objects.filter(name__icontains='Public Admin', level='diploma2').first()

try:
    BUS = Programme.objects.get(code='BUS', level='diploma1')
    BUS2 = Programme.objects.get(code='BUS', level='diploma2')
except Programme.DoesNotExist:
    BUS = Programme.objects.filter(name__icontains='Business', level='diploma1').first()
    BUS2 = Programme.objects.filter(name__icontains='Business', level='diploma2').first()

print(f"PAD Diploma I:  {PAD}")
print(f"PAD Diploma II: {PAD2}")
print(f"BUS Diploma I:  {BUS}")
print(f"BUS Diploma II: {BUS2}")
print("-" * 60)

COURSES = [
    # ── PUBLIC ADMINISTRATION — DIPLOMA I — SEMESTER 1 ──────
    {'code':'BUS111','title':'Introduction to Business I',           'unit':2,'prog':PAD, 'sem':1},
    {'code':'BUS113','title':'Principles of Economics',              'unit':2,'prog':PAD, 'sem':1},
    {'code':'COM111','title':'Introduction to Computer',             'unit':2,'prog':PAD, 'sem':1},
    {'code':'GNS111','title':'Use of English and Communication Skills','unit':2,'prog':PAD,'sem':1},
    {'code':'GNS112','title':'Citizenship Education',                'unit':2,'prog':PAD, 'sem':1},
    {'code':'PAD111','title':'Elements of Public Administration',    'unit':3,'prog':PAD, 'sem':1},
    {'code':'PAD112','title':'Introduction to Psychology',           'unit':2,'prog':PAD, 'sem':1},

    # ── PUBLIC ADMINISTRATION — DIPLOMA I — SEMESTER 2 ──────
    {'code':'BUS121','title':'Introduction to Business II',          'unit':2,'prog':PAD, 'sem':2},
    {'code':'GNS121','title':'Use of English II',                    'unit':2,'prog':PAD, 'sem':2},
    {'code':'PAD121','title':'Public Policy Making',                 'unit':2,'prog':PAD, 'sem':2},
    {'code':'PAD122','title':'Nigerian Government and Politics',     'unit':2,'prog':PAD, 'sem':2},
    {'code':'PAD123','title':'Administrative Law',                   'unit':2,'prog':PAD, 'sem':2},
    {'code':'PAD124','title':'Introduction to Community Development','unit':2,'prog':PAD, 'sem':2},
    {'code':'PAD125','title':'Basic Research Methodology',           'unit':3,'prog':PAD, 'sem':2},
    {'code':'GNS123','title':'Use of Library',                       'unit':2,'prog':PAD, 'sem':2},

    # ── PUBLIC ADMINISTRATION — DIPLOMA II — SEMESTER 3 ─────
    {'code':'GNS211','title':'Entrepreneurship Studies',             'unit':3,'prog':PAD2,'sem':3},
    {'code':'PAD211','title':'Introduction to Public Finance',       'unit':3,'prog':PAD2,'sem':3},
    {'code':'PAD212','title':'Principles of Human Resource Management','unit':3,'prog':PAD2,'sem':3},
    {'code':'PAD213','title':'Public Service Rules',                 'unit':2,'prog':PAD2,'sem':3},
    {'code':'PAD214','title':'Theories of Management / Administration','unit':2,'prog':PAD2,'sem':3},
    {'code':'PAD215','title':'Introduction to E-Governance',         'unit':2,'prog':PAD2,'sem':3},

    # ── PUBLIC ADMINISTRATION — DIPLOMA II — SEMESTER 4 ─────
    {'code':'GNS221','title':'Small Business Management',            'unit':3,'prog':PAD2,'sem':4},
    {'code':'PAD221','title':'Introduction to Inter Governmental Relations','unit':3,'prog':PAD2,'sem':4},
    {'code':'PAD222','title':'Social and Economic Development',      'unit':3,'prog':PAD2,'sem':4},
    {'code':'PAD223','title':'Introduction to Industrial Relations', 'unit':2,'prog':PAD2,'sem':4},
    {'code':'PAD224','title':'Public Enterprise Management',         'unit':2,'prog':PAD2,'sem':4},
    {'code':'PAD225','title':'Project',                              'unit':4,'prog':PAD2,'sem':4},
    {'code':'SDV221','title':'Principles of Conflict Management',    'unit':3,'prog':PAD2,'sem':4},

    # ── BUSINESS ADMINISTRATION — DIPLOMA I — SEMESTER 1 ────
    {'code':'ACC111','title':'Principles of Accounting',             'unit':2,'prog':BUS, 'sem':1},
    {'code':'BUS111','title':'Introduction to Business I',           'unit':3,'prog':BUS, 'sem':1},
    {'code':'BUS112','title':'Business Mathematics',                 'unit':3,'prog':BUS, 'sem':1},
    {'code':'BUS113','title':'Principles of Economics',              'unit':2,'prog':BUS, 'sem':1},
    {'code':'COM111','title':'Introduction to Computer',             'unit':2,'prog':BUS, 'sem':1},
    {'code':'GNS111','title':'Use of English and Communication Skills','unit':2,'prog':BUS,'sem':1},
    {'code':'GNS112','title':'Citizenship Education',                'unit':2,'prog':BUS, 'sem':1},

    # ── BUSINESS ADMINISTRATION — DIPLOMA I — SEMESTER 2 ────
    {'code':'ACC121','title':'Financial Accounting',                 'unit':3,'prog':BUS, 'sem':2},
    {'code':'BUS121','title':'Introduction to Business II',          'unit':3,'prog':BUS, 'sem':2},
    {'code':'BUS122','title':'Business Statistics',                  'unit':2,'prog':BUS, 'sem':2},
    {'code':'BUS123','title':'Introduction to Finance',              'unit':2,'prog':BUS, 'sem':2},
    {'code':'BUS124','title':'Basic Research Methodology',           'unit':3,'prog':BUS, 'sem':2},
    {'code':'COM123','title':'Computer Application Packages',        'unit':2,'prog':BUS, 'sem':2},
    {'code':'GNS121','title':'Use of English II',                    'unit':2,'prog':BUS, 'sem':2},
    {'code':'GNS123','title':'Use of Library',                       'unit':2,'prog':BUS, 'sem':2},

    # ── BUSINESS ADMINISTRATION — DIPLOMA II — SEMESTER 3 ───
    {'code':'BUS211','title':'Principles of Management I',           'unit':3,'prog':BUS2,'sem':3},
    {'code':'BUS212','title':'Elements of Human Capital Management', 'unit':3,'prog':BUS2,'sem':3},
    {'code':'BUS213','title':'Principles of Marketing',              'unit':2,'prog':BUS2,'sem':3},
    {'code':'BUS214','title':'Introduction to E-Business',           'unit':2,'prog':BUS2,'sem':3},
    {'code':'BUS215','title':'Business Communication',               'unit':2,'prog':BUS2,'sem':3},
    {'code':'BUS216','title':'Introduction to Islamic Business Ethics','unit':3,'prog':BUS2,'sem':3},
    {'code':'GNS211','title':'Entrepreneurship Studies',             'unit':3,'prog':BUS2,'sem':3},

    # ── BUSINESS ADMINISTRATION — DIPLOMA II — SEMESTER 4 ───
    {'code':'ACC224','title':'Cost and Management Accounting',       'unit':3,'prog':BUS2,'sem':4},
    {'code':'BUS221','title':'Principles of Management II',          'unit':2,'prog':BUS2,'sem':4},
    {'code':'BUS222','title':'Introduction to Islamic Banking and Finance','unit':2,'prog':BUS2,'sem':4},
    {'code':'BUS223','title':'Principles of Insurance',              'unit':2,'prog':BUS2,'sem':4},
    {'code':'BUS224','title':'Business Law',                         'unit':3,'prog':BUS2,'sem':4},
    {'code':'BUS225','title':'Project',                              'unit':4,'prog':BUS2,'sem':4},
    {'code':'GNS221','title':'Small Business Management',            'unit':3,'prog':BUS2,'sem':4},
]

created = skipped = errors = 0

for c in COURSES:
    if not c['prog']:
        print(f"  SKIP  {c['code']} — programme not found")
        skipped += 1
        continue
    exists = Course.objects.filter(
        code=c['code'], programme=c['prog'], semester_number=c['sem']
    ).exists()
    if exists:
        print(f"  SKIP  {c['code']} — {c['title']} (already exists)")
        skipped += 1
        continue
    try:
        Course.objects.create(
            code=c['code'],
            title=c['title'],
            unit=c['unit'],
            programme=c['prog'],
            semester_number=c['sem'],
        )
        prog_label = f"{c['prog'].code} Dip{'I' if c['prog'].level=='diploma1' else 'II'} Sem{c['sem']}"
        print(f"  OK    {c['code']} — {c['title']} ({prog_label})")
        created += 1
    except Exception as e:
        print(f"  ERROR {c['code']} — {c['title']}: {e}")
        errors += 1

print("-" * 60)
print(f"DONE: {created} created | {skipped} skipped | {errors} errors")
print(f"Total courses in DB: {Course.objects.count()}")
