# ============================================================
# 1. ADD TO students/admin.py
# ============================================================
import csv, io
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from .models import Student
from academics.models import Programme
from core.models import Session, Semester

User = get_user_model()


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display  = ['reg_number', 'get_full_name', 'programme', 'current_session', 'status']
    list_filter   = ['status', 'programme', 'current_session']
    search_fields = ['reg_number', 'user__first_name', 'user__last_name', 'user__email']
    list_per_page = 30

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'

    # ── Custom URLs ──────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('import-csv/',
                 self.admin_site.admin_view(self.import_csv_view),
                 name='import_students_csv'),
            path('download-template/',
                 self.admin_site.admin_view(self.download_template),
                 name='download_student_csv_template'),
            path('export-csv/',
                 self.admin_site.admin_view(self.export_csv),
                 name='export_students_csv'),
        ]
        return custom + urls

    # ── Change list button ────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_csv_url'] = 'import-csv/'
        return super().changelist_view(request, extra_context=extra_context)

    # ── Save model (handles webcam photo too) ────────────────
    import base64, uuid
    from django.core.files.base import ContentFile

    def save_model(self, request, obj, form, change):
        webcam_data = request.POST.get('webcam_photo', '')
        if webcam_data and webcam_data.startswith('data:image'):
            import base64, uuid
            from django.core.files.base import ContentFile
            img_data = webcam_data.split(',')[1]
            img_file = ContentFile(
                base64.b64decode(img_data),
                name=f'student_{uuid.uuid4()}.jpg'
            )
            obj.photo.save(img_file.name, img_file, save=False)
        super().save_model(request, obj, form, change)

    # ── CSV Import View ───────────────────────────────────────
    def import_csv_view(self, request):
        results = None

        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')

            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a valid .csv file.')
                return redirect('.')

            if csv_file.size > 5 * 1024 * 1024:
                messages.error(request, 'File too large. Maximum size is 5 MB.')
                return redirect('.')

            decoded  = csv_file.read().decode('utf-8-sig')
            reader   = csv.DictReader(io.StringIO(decoded))

            # validate headers
            required = {'first_name','last_name','email','username','password','reg_number','programme'}
            missing  = required - set(reader.fieldnames or [])
            if missing:
                messages.error(request, f'Missing columns: {", ".join(missing)}')
                return redirect('.')

            rows = []
            created = skipped = errors = 0

            for i, row in enumerate(reader, start=1):
                reg   = row.get('reg_number','').strip()
                fname = row.get('first_name','').strip()
                lname = row.get('last_name','').strip()
                email = row.get('email','').strip()
                uname = row.get('username','').strip()
                pwd   = row.get('password','').strip()
                prog  = row.get('programme','').strip()
                sess  = row.get('session','').strip()
                sem   = row.get('semester','').strip()
                stat  = row.get('status','Active').strip()

                if not reg or not uname:
                    rows.append({'reg_number': reg or f'Row {i}', 'name': f'{fname} {lname}',
                                 'programme': prog, 'status': 'Error',
                                 'status_class': 'err', 'note': 'Missing reg_number or username'})
                    errors += 1
                    continue

                # skip duplicates
                if User.objects.filter(username=uname).exists() or Student.objects.filter(reg_number=reg).exists():
                    rows.append({'reg_number': reg, 'name': f'{fname} {lname}',
                                 'programme': prog, 'status': 'Skipped',
                                 'status_class': 'skip', 'note': 'Already exists'})
                    skipped += 1
                    continue

                try:
                    user = User.objects.create_user(
                        username=uname, email=email,
                        first_name=fname, last_name=lname,
                        password=pwd
                    )

                    programme_obj = Programme.objects.filter(name__iexact=prog).first()
                    session_obj   = Session.objects.filter(name__iexact=sess).first()   if sess else None
                    semester_obj  = Semester.objects.filter(name__iexact=sem).first()   if sem  else None

                    Student.objects.create(
                        user=user,
                        reg_number=reg,
                        programme=programme_obj,
                        current_session=session_obj,
                        current_semester=semester_obj,
                        status=stat,
                    )

                    # optional welcome email
                    if request.POST.get('send_welcome_email'):
                        from django.core.mail import send_mail
                        send_mail(
                            subject='Welcome to CMT Portal',
                            message=f'Dear {fname},\n\nYour account has been created.\nUsername: {uname}\nPassword: {pwd}\n\nPlease login and change your password.',
                            from_email=None,
                            recipient_list=[email],
                            fail_silently=True,
                        )

                    rows.append({'reg_number': reg, 'name': f'{fname} {lname}',
                                 'programme': prog, 'status': 'Created',
                                 'status_class': 'ok', 'note': '—'})
                    created += 1

                except Exception as e:
                    rows.append({'reg_number': reg, 'name': f'{fname} {lname}',
                                 'programme': prog, 'status': 'Error',
                                 'status_class': 'err', 'note': str(e)})
                    errors += 1

            results = {
                'total': created + skipped + errors,
                'created': created,
                'skipped': skipped,
                'errors': errors,
                'rows': rows,
            }

            if created:
                messages.success(request, f'✅ {created} student(s) imported successfully.')
            if errors:
                messages.error(request, f'⚠ {errors} row(s) had errors — see details below.')

        context = {**self.admin_site.each_context(request), 'results': results, 'title': 'Import Students CSV'}
        return render(request, 'admin/students/student/import_students.html', context)

    # ── Download blank template ───────────────────────────────
    def download_template(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="student_import_template.csv"'
        writer = csv.writer(response)
        writer.writerow(['first_name','last_name','email','username','password',
                         'reg_number','programme','session','semester','status'])
        writer.writerow(['John','Doe','john@cmt.edu.ng','CMT2024001','Pass1234!',
                         'CMT/2024/001','DIPLOMA PUBLIC ADMINISTRATION','2025/2026','First Semester','Active'])
        writer.writerow(['Fatima','Bello','fatima@cmt.edu.ng','CMT2024002','Pass1234!',
                         'CMT/2024/002','EDUCATION (ISLAMIC STUDIES)','2025/2026','Second Semester','Active'])
        return response

    # ── Export existing students ──────────────────────────────
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="students_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['first_name','last_name','email','username','reg_number',
                         'programme','session','semester','status'])
        for s in Student.objects.select_related('user','programme','current_session','current_semester').all():
            writer.writerow([
                s.user.first_name, s.user.last_name, s.user.email, s.user.username,
                s.reg_number,
                s.programme.name if s.programme else '',
                s.current_session.name if s.current_session else '',
                s.current_semester.name if s.current_semester else '',
                s.status,
            ])
        return response