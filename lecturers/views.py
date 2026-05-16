from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q

from .models import Lecturer, LecturerCourse
from .forms import LecturerCreateForm, LecturerUpdateForm, LecturerCourseAssignmentForm


def registrar_required(view_func):
    """Allow superuser, admin, registrar, or academic_officer."""
    @login_required
    def wrapper(request, *args, **kwargs):
        u = request.user
        if u.is_superuser or u.role in ('admin', 'registrar', 'academic_officer'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You don't have access to manage lecturers.")
    return wrapper


@registrar_required
def lecturer_list(request):
    q = request.GET.get('q', '').strip()
    qs = Lecturer.objects.select_related('user').all()
    if q:
        qs = qs.filter(
            Q(staff_id__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(department__icontains=q)
        )
    return render(request, 'lecturers/list.html', {'lecturers': qs, 'q': q})


@registrar_required
def lecturer_create(request):
    if request.method == 'POST':
        form = LecturerCreateForm(request.POST, request.FILES)
        if form.is_valid():
            lec = form.save()
            messages.success(
                request,
                f"Lecturer {lec.full_name} created. Username: {lec.user.username} | Initial password: {lec.staff_id}"
            )
            return redirect('lecturers:detail', pk=lec.pk)
    else:
        form = LecturerCreateForm()
    return render(request, 'lecturers/form.html', {'form': form, 'mode': 'create'})


@registrar_required
def lecturer_detail(request, pk):
    lecturer = get_object_or_404(Lecturer.objects.select_related('user'), pk=pk)
    assignments = lecturer.course_assignments.select_related('course', 'semester').all()
    return render(request, 'lecturers/detail.html', {
        'lecturer': lecturer,
        'assignments': assignments,
        'assign_form': LecturerCourseAssignmentForm(),
    })


@registrar_required
def lecturer_update(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    if request.method == 'POST':
        form = LecturerUpdateForm(request.POST, request.FILES, instance=lecturer)
        if form.is_valid():
            form.save()
            messages.success(request, "Lecturer updated.")
            return redirect('lecturers:detail', pk=lecturer.pk)
    else:
        form = LecturerUpdateForm(instance=lecturer)
    return render(request, 'lecturers/form.html', {'form': form, 'mode': 'update', 'lecturer': lecturer})


@registrar_required
def assign_course(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    if request.method != 'POST':
        return redirect('lecturers:detail', pk=pk)
    form = LecturerCourseAssignmentForm(request.POST)
    if form.is_valid():
        try:
            a = form.save(commit=False)
            a.lecturer = lecturer
            a.assigned_by = request.user
            a.save()
            messages.success(request, f"Assigned {a.course} ({a.semester}) to {lecturer.full_name}.")
        except Exception as e:
            messages.error(request, f"Could not assign: {e}")
    else:
        for field, errs in form.errors.items():
            for err in errs:
                messages.error(request, f"{field}: {err}")
    return redirect('lecturers:detail', pk=pk)


@registrar_required
def toggle_assignment(request, pk):
    a = get_object_or_404(LecturerCourse, pk=pk)
    a.is_active = not a.is_active
    a.save(update_fields=['is_active'])
    messages.info(request, f"Assignment {'activated' if a.is_active else 'deactivated'}.")
    return redirect('lecturers:detail', pk=a.lecturer_id)


@registrar_required
def delete_assignment(request, pk):
    a = get_object_or_404(LecturerCourse, pk=pk)
    lec_pk = a.lecturer_id
    label = str(a.course)
    a.delete()
    messages.info(request, f"Removed assignment for {label}.")
    return redirect('lecturers:detail', pk=lec_pk)


@registrar_required
def reset_password(request, pk):
    lecturer = get_object_or_404(Lecturer, pk=pk)
    if request.method == 'POST':
        u = lecturer.user
        u.set_password(lecturer.staff_id)
        u.must_change_password = True
        u.save()
        messages.success(request, f"Password reset to staff ID '{lecturer.staff_id}'. They must change it on next login.")
    return redirect('lecturers:detail', pk=pk)

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
        'quiz_count': Quiz.objects.filter(created_by__user=request.user).count(),
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

# ============================================================
# Phase 1B — Quiz lecturer-side views
# ============================================================
from django.db import transaction as _qtx
from .models import Quiz, Question, Choice
from .forms import QuizForm, QuestionForm, ChoiceForm


def _own_quiz_or_403(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related('course', 'semester', 'created_by'), pk=pk)
    if quiz.created_by != request.user.lecturer_profile:
        return None, HttpResponseForbidden("This quiz isn't yours.")
    return quiz, None


@lecturer_required
def quiz_list(request):
    lecturer = request.user.lecturer_profile
    quizzes = (Quiz.objects.filter(created_by=lecturer)
               .select_related('course', 'semester').order_by('-created_at'))
    return render(request, 'lecturers/quiz_list.html', {'lecturer': lecturer, 'quizzes': quizzes})


@lecturer_required
def quiz_create(request):
    lecturer = request.user.lecturer_profile
    if request.method == 'POST':
        form = QuizForm(request.POST, lecturer=lecturer)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = lecturer
            quiz.save()
            messages.success(request, f"Created '{quiz.title}'. Now add its questions and choices.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    else:
        form = QuizForm(lecturer=lecturer)
    return render(request, 'lecturers/quiz_form.html', {'form': form, 'mode': 'create'})


@lecturer_required
def quiz_update(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz, lecturer=request.user.lecturer_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz settings updated.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    else:
        form = QuizForm(instance=quiz, lecturer=request.user.lecturer_profile)
    return render(request, 'lecturers/quiz_form.html', {'form': form, 'mode': 'update', 'quiz': quiz})


@lecturer_required
def quiz_detail(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    questions = quiz.questions.prefetch_related('choices').order_by('order', 'id')
    return render(request, 'lecturers/quiz_detail.html', {
        'quiz': quiz, 'questions': questions,
        'question_form': QuestionForm(), 'choice_form': ChoiceForm(),
    })


@lecturer_required
def quiz_publish(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method != 'POST':
        return redirect('lecturers:quiz_detail', pk=quiz.pk)
    if not quiz.is_published:
        if quiz.questions.count() == 0:
            messages.error(request, "Add at least one question before publishing.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
        bad = [q for q in quiz.questions.prefetch_related('choices') if not q.is_ready]
        if bad:
            messages.error(request, f"{len(bad)} question(s) need at least 2 choices and exactly one marked correct.")
            return redirect('lecturers:quiz_detail', pk=quiz.pk)
    quiz.is_published = not quiz.is_published
    quiz.save(update_fields=['is_published', 'updated_at'])
    messages.success(request, f"Quiz {'published' if quiz.is_published else 'unpublished'}.")
    return redirect('lecturers:quiz_detail', pk=quiz.pk)


@lecturer_required
def quiz_delete(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        title = quiz.title
        quiz.delete()
        messages.info(request, f"Deleted '{title}'.")
        return redirect('lecturers:quiz_list')
    return redirect('lecturers:quiz_detail', pk=pk)


@lecturer_required
def question_create(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.quiz = quiz
            q.order = quiz.questions.count() + 1
            q.save()
            messages.success(request, "Question added. Now add at least 2 choices and mark one correct.")
        else:
            for f, errs in form.errors.items():
                for e in errs: messages.error(request, f"{f}: {e}")
    return redirect('lecturers:quiz_detail', pk=pk)


@lecturer_required
def question_delete(request, pk):
    question = get_object_or_404(Question.objects.select_related('quiz'), pk=pk)
    if question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your question.")
    quiz_pk = question.quiz_id
    if request.method == 'POST':
        question.delete()
        messages.info(request, "Question removed.")
    return redirect('lecturers:quiz_detail', pk=quiz_pk)


@lecturer_required
def choice_create(request, pk):
    question = get_object_or_404(Question.objects.select_related('quiz'), pk=pk)
    if question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your question.")
    if request.method == 'POST':
        form = ChoiceForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.question = question
            c.order = question.choices.count() + 1
            c.save()
        else:
            for f, errs in form.errors.items():
                for e in errs: messages.error(request, f"{f}: {e}")
    return redirect('lecturers:quiz_detail', pk=question.quiz_id)


@lecturer_required
def choice_delete(request, pk):
    choice = get_object_or_404(Choice.objects.select_related('question__quiz'), pk=pk)
    if choice.question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your choice.")
    quiz_pk = choice.question.quiz_id
    if request.method == 'POST':
        choice.delete()
    return redirect('lecturers:quiz_detail', pk=quiz_pk)


@lecturer_required
def choice_mark_correct(request, pk):
    choice = get_object_or_404(Choice.objects.select_related('question__quiz'), pk=pk)
    if choice.question.quiz.created_by != request.user.lecturer_profile:
        return HttpResponseForbidden("Not your choice.")
    if request.method == 'POST':
        with _qtx.atomic():
            choice.question.choices.update(is_correct=False)
            choice.is_correct = True
            choice.save(update_fields=['is_correct'])
    return redirect('lecturers:quiz_detail', pk=choice.question.quiz_id)

# ============================================================
# Phase 1B.1c — CSV bulk import of quiz questions
# ============================================================
import csv as _csv
import io as _io


@lecturer_required
def quiz_import_csv(request, pk):
    quiz, denial = _own_quiz_or_403(request, pk)
    if denial: return denial
    if request.method == 'POST':
        f = request.FILES.get('csv_file')
        if not f:
            messages.error(request, "Choose a CSV file to upload.")
            return redirect('lecturers:quiz_import', pk=pk)
        try:
            text = f.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, "File must be UTF-8 encoded CSV.")
            return redirect('lecturers:quiz_import', pk=pk)
        rows = list(_csv.reader(_io.StringIO(text)))
        if not rows:
            messages.error(request, "CSV is empty.")
            return redirect('lecturers:quiz_import', pk=pk)
        # Auto-skip header if it looks like one
        first = rows[0]
        if first and any((c or '').strip().lower() in ('question','correct','correct_answer','answer','option') for c in first):
            rows = rows[1:]
        if not rows:
            messages.error(request, "CSV has only a header row.")
            return redirect('lecturers:quiz_import', pk=pk)
        errors = []
        for i, row in enumerate(rows, start=1):
            if len(row) < 3:
                errors.append(f"Row {i}: need at least 3 columns (question, correct, >=1 wrong option). Got {len(row)}.")
            elif not (row[0] or '').strip():
                errors.append(f"Row {i}: question text is empty.")
            elif not (row[1] or '').strip():
                errors.append(f"Row {i}: correct answer is empty.")
            elif not any((c or '').strip() for c in row[2:]):
                errors.append(f"Row {i}: no wrong options.")
        if errors:
            for e in errors[:10]:
                messages.error(request, e)
            if len(errors) > 10:
                messages.error(request, f"... and {len(errors) - 10} more error(s).")
            return redirect('lecturers:quiz_import', pk=pk)
        created_q = created_c = 0
        with _qtx.atomic():
            base = quiz.questions.count()
            for i, row in enumerate(rows, start=1):
                qtext   = row[0].strip()
                correct = row[1].strip()
                wrongs  = [(c or '').strip() for c in row[2:] if (c or '').strip()]
                q = Question.objects.create(quiz=quiz, text=qtext, points=1, order=base + i)
                created_q += 1
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                created_c += 1
                for j, w in enumerate(wrongs, start=2):
                    Choice.objects.create(question=q, text=w, is_correct=False, order=j)
                    created_c += 1
        messages.success(request, f"Imported {created_q} questions ({created_c} choices total).")
        return redirect('lecturers:quiz_detail', pk=pk)
    return render(request, 'lecturers/quiz_import.html', {'quiz': quiz})

# ============================================================
# Phase 1B.2 — Student-side quiz views
# ============================================================
import datetime as _dt
import random as _rnd
from django.utils import timezone as _tz
from .models import QuizAttempt, AttemptAnswer


def student_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        u = request.user
        if u.role == 'student' and hasattr(u, 'student'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("This area is for students only.")
    return wrapper


@student_required
def student_quiz_list(request):
    from academics.models import CourseRegistration
    student = request.user.student
    pairs = set(CourseRegistration.objects.filter(
        student=student, status__in=['registered', 'carryover']
    ).values_list('course_id', 'semester_id'))
    quizzes = (Quiz.objects.filter(is_published=True)
               .select_related('course', 'semester')
               .order_by('-available_from'))
    visible = [q for q in quizzes if (q.course_id, q.semester_id) in pairs]
    by_quiz = {a.quiz_id: a for a in QuizAttempt.objects.filter(student=student, quiz__in=visible)}
    items = [{'quiz': q, 'attempt': by_quiz.get(q.id)} for q in visible]
    return render(request, 'lecturers/student_quiz_list.html', {'items': items, 'student': student})


@student_required
def quiz_start(request, pk):
    if request.method != 'POST':
        return redirect('lecturers:student_quiz_list')
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True)
    student = request.user.student
    from academics.models import CourseRegistration
    if not CourseRegistration.objects.filter(
        student=student, course=quiz.course, semester=quiz.semester,
        status__in=['registered', 'carryover']
    ).exists():
        return HttpResponseForbidden("You are not registered for this course.")
    now = _tz.now()
    if now < quiz.available_from:
        messages.error(request, "Quiz is not yet open.")
        return redirect('lecturers:student_quiz_list')
    if now > quiz.available_until:
        messages.error(request, "This quiz has closed.")
        return redirect('lecturers:student_quiz_list')
    existing = QuizAttempt.objects.filter(quiz=quiz, student=student).first()
    if existing:
        if existing.is_submitted:
            messages.info(request, "You've already submitted this quiz.")
            return redirect('lecturers:quiz_attempt_result', pk=existing.pk)
        return redirect('lecturers:quiz_take', pk=existing.pk)
    bank = list(quiz.questions.prefetch_related('choices').all())
    bank = [q for q in bank if q.is_ready]
    if not bank:
        messages.error(request, "This quiz has no ready questions. Contact your lecturer.")
        return redirect('lecturers:student_quiz_list')
    n = min(quiz.questions_to_attempt or len(bank), len(bank))
    selected = _rnd.sample(bank, n)
    _rnd.shuffle(selected)
    with _qtx.atomic():
        attempt = QuizAttempt.objects.create(quiz=quiz, student=student, max_score=quiz.max_score)
        for i, q in enumerate(selected, start=1):
            AttemptAnswer.objects.create(attempt=attempt, question=q, order=i)
    return redirect('lecturers:quiz_take', pk=attempt.pk)


@student_required
def quiz_take(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'student'),
        pk=pk, student=request.user.student,
    )
    if attempt.is_submitted:
        return redirect('lecturers:quiz_attempt_result', pk=attempt.pk)
    quiz = attempt.quiz
    now = _tz.now()
    deadline = None
    if quiz.time_limit_minutes:
        deadline = attempt.started_at + _dt.timedelta(minutes=quiz.time_limit_minutes)
    effective = min(deadline, quiz.available_until) if deadline else quiz.available_until
    if now > effective:
        return _finalize_attempt(request, attempt, auto=True)
    if request.method == 'POST':
        with _qtx.atomic():
            for a in attempt.answers.select_related('question').all():
                cid = request.POST.get(f'q_{a.question_id}')
                if cid:
                    try:
                        choice = Choice.objects.get(pk=int(cid), question=a.question)
                        a.selected_choice = choice
                        a.save(update_fields=['selected_choice'])
                    except (Choice.DoesNotExist, ValueError):
                        pass
        return _finalize_attempt(request, attempt, auto=False)
    rng = _rnd.Random(attempt.pk)
    items = []
    for a in attempt.answers.select_related('question').prefetch_related('question__choices').order_by('order'):
        choices = list(a.question.choices.all())
        rng.shuffle(choices)
        items.append({'answer': a, 'question': a.question, 'choices': choices})
    remaining = int((effective - now).total_seconds())
    return render(request, 'lecturers/take_quiz.html', {
        'attempt': attempt, 'quiz': quiz,
        'questions_data': items,
        'remaining_seconds': remaining,
        'has_time_limit': bool(deadline),
    })


def _finalize_attempt(request, attempt, auto=False):
    answers = list(attempt.answers.select_related('selected_choice').all())
    asked = len(answers)
    correct = sum(1 for a in answers if a.selected_choice_id and a.selected_choice.is_correct)
    score = round((correct / asked) * float(attempt.max_score), 2) if asked else 0
    attempt.score = score
    attempt.is_submitted = True
    attempt.auto_submitted = auto
    attempt.submitted_at = _tz.now()
    attempt.save(update_fields=['score', 'is_submitted', 'auto_submitted', 'submitted_at'])
    messages.success(request, "Your quiz has been submitted.")
    return redirect('lecturers:quiz_attempt_result', pk=attempt.pk)


@student_required
def quiz_attempt_result(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'quiz__course', 'quiz__semester'),
        pk=pk, student=request.user.student,
    )
    show_score = _tz.now() > attempt.quiz.available_until
    return render(request, 'lecturers/quiz_result.html', {
        'attempt': attempt, 'quiz': attempt.quiz, 'show_score': show_score,
    })

# ============================================================
# Phase 1B.3 — Results & CA Aggregation (lecturer-facing)
# ============================================================

def _can_view_results(user, quiz):
    if user.is_superuser: return True
    if getattr(user, 'role', None) in ('admin', 'registrar', 'academic_officer'): return True
    if getattr(user, 'role', None) == 'lecturer':
        return bool(quiz.created_by) and quiz.created_by.user_id == user.id
    return False


def _can_view_course_results(user, course, semester):
    if user.is_superuser: return True
    if getattr(user, 'role', None) in ('admin', 'registrar', 'academic_officer'): return True
    if getattr(user, 'role', None) == 'lecturer':
        return LecturerCourse.objects.filter(
            lecturer__user=user, course=course, semester=semester, is_active=True
        ).exists()
    return False


@login_required
def quiz_attempts(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related('course', 'semester'), pk=pk)
    if not _can_view_results(request.user, quiz):
        return HttpResponseForbidden("You don't have permission to view these attempts.")
    attempts = list(QuizAttempt.objects
                    .filter(quiz=quiz)
                    .select_related('student', 'student__user')
                    .order_by('-is_submitted', '-score', 'student__reg_number'))
    submitted = [a for a in attempts if a.is_submitted]
    n = len(submitted)
    avg = round(sum(float(a.score or 0) for a in submitted) / n, 2) if n else 0
    hi  = round(max((float(a.score or 0) for a in submitted), default=0), 2)
    lo  = round(min((float(a.score or 0) for a in submitted), default=0), 2)
    return render(request, 'lecturers/quiz_attempts.html', {
        'quiz': quiz, 'attempts': attempts,
        'submitted_count': n,
        'in_progress_count': len(attempts) - n,
        'avg_score': avg, 'hi': hi, 'lo': lo,
    })


@login_required
def attempt_inspect(request, pk):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related('quiz', 'quiz__course', 'quiz__semester', 'student', 'student__user'),
        pk=pk,
    )
    if not _can_view_results(request.user, attempt.quiz):
        return HttpResponseForbidden("You don't have permission.")
    answers = list(attempt.answers
                   .select_related('question', 'selected_choice')
                   .prefetch_related('question__choices')
                   .order_by('order'))
    items = []
    for a in answers:
        choices = list(a.question.choices.all())
        correct = next((c for c in choices if c.is_correct), None)
        items.append({'answer': a, 'question': a.question, 'choices': choices, 'correct': correct})
    return render(request, 'lecturers/attempt_inspect.html', {
        'attempt': attempt, 'quiz': attempt.quiz, 'items': items,
    })


@login_required
def course_results(request, course_id, semester_id):
    from academics.models import Course, CourseRegistration
    from core.models import Semester
    course   = get_object_or_404(Course, pk=course_id)
    semester = get_object_or_404(Semester, pk=semester_id)
    if not _can_view_course_results(request.user, course, semester):
        return HttpResponseForbidden("You are not assigned to this course.")
    quizzes = list(Quiz.objects.filter(course=course, semester=semester, is_published=True).order_by('available_from'))
    regs = (CourseRegistration.objects
            .filter(course=course, semester=semester, status__in=['registered', 'carryover'])
            .select_related('student', 'student__user')
            .order_by('student__reg_number'))
    score_map = {(a.student_id, a.quiz_id): a for a in
                 QuizAttempt.objects.filter(quiz__in=quizzes, is_submitted=True)}
    max_total = sum(q.max_score for q in quizzes)
    rows = []
    for r in regs:
        s = r.student
        cells = []
        total = 0.0
        for q in quizzes:
            att = score_map.get((s.id, q.id))
            cells.append({'quiz': q, 'attempt': att, 'score': att.score if att else None})
            if att and att.score is not None:
                total += float(att.score)
        rows.append({'student': s, 'cells': cells, 'total': round(total, 2)})
    rows.sort(key=lambda r: -r['total'])
    return render(request, 'lecturers/course_results.html', {
        'course': course, 'semester': semester,
        'quizzes': quizzes, 'rows': rows, 'max_total': max_total,
    })



# ============ ASSIGNMENT VIEWS (Phase 1C) ============
from django.utils import timezone
from .models import Assignment, AssignmentGroup, IndividualSubmission, GroupSubmission


@login_required
def assignment_list(request):
    """List assignments - filtered by user role"""
    user = request.user
    if getattr(user, 'role', None) == 'lecturer':
        assignments = Assignment.objects.filter(created_by__user=user)
    elif user.is_superuser or getattr(user, 'role', None) in ['admin', 'registrar', 'academic_officer']:
        assignments = Assignment.objects.all()
    else:
        assignments = Assignment.objects.none()
    
    return render(request, 'lecturers/assignment_list.html', {'assignments': assignments})


@login_required
def assignment_create(request):
    """Create new assignment"""
    if getattr(request.user, 'role', None) != 'lecturer':
        return HttpResponseForbidden('Only lecturers can create assignments')
    
    from academics.models import Course
    from core.models import Semester
    
    # Get lecturer's courses
    lecturer = Lecturer.objects.filter(user=request.user).first()
    if not lecturer:
        return HttpResponseForbidden('Lecturer profile not found')
    
    courses = Course.objects.filter(lecturers=lecturer) if hasattr(Course, 'lecturers') else Course.objects.all()
    semesters = Semester.objects.all().order_by('-id')
    
    if request.method == 'POST':
        course_id = request.POST.get('course')
        semester_id = request.POST.get('semester')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        ind_deadline = request.POST.get('individual_deadline')
        grp_deadline = request.POST.get('group_deadline')
        is_published = request.POST.get('is_published') == 'on'
        
        if not all([course_id, semester_id, title, description, ind_deadline, grp_deadline]):
            messages.error(request, 'All fields are required')
        else:
            assignment = Assignment.objects.create(
                course_id=course_id,
                semester_id=semester_id,
                title=title,
                description=description,
                individual_deadline=ind_deadline,
                group_deadline=grp_deadline,
                created_by=lecturer,
                is_published=is_published
            )
            messages.success(request, f'Assignment "{title}" created!')
            return redirect('lecturers:assignment_detail', pk=assignment.pk)
    
    return render(request, 'lecturers/assignment_create.html', {
        'courses': courses,
        'semesters': semesters,
    })


@login_required
def assignment_detail(request, pk):
    """View assignment with submission stats"""
    assignment = get_object_or_404(Assignment, pk=pk)
    
    user = request.user
    can_edit = user.is_superuser or (assignment.created_by and assignment.created_by.user_id == user.id)
    
    # Count submissions
    individual_count = assignment.individual_submissions.count()
    group_count = GroupSubmission.objects.filter(group__assignment=assignment).count()
    total_groups = assignment.groups.count()
    
    return render(request, 'lecturers/assignment_detail.html', {
        'assignment': assignment,
        'can_edit': can_edit,
        'individual_count': individual_count,
        'group_count': group_count,
        'total_groups': total_groups,
        'groups': assignment.groups.all().prefetch_related('members', 'leader'),
    })


@login_required
def assignment_groups(request, pk):
    """Manage groups for an assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)
    
    user = request.user
    if not (user.is_superuser or (assignment.created_by and assignment.created_by.user_id == user.id)):
        return HttpResponseForbidden('Permission denied')
    
    from students.models import Student
    from students.models import CourseRegistration
    
    # Get students registered for this course in this semester
    registered_students = Student.objects.filter(
        courseregistration__course=assignment.course,
        courseregistration__semester=assignment.semester
    ).distinct() if hasattr(Student, 'courseregistration') else Student.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_group':
            name = request.POST.get('group_name', '').strip()
            if name:
                AssignmentGroup.objects.get_or_create(assignment=assignment, name=name)
                messages.success(request, f'Created {name}')
        
        elif action == 'assign_member':
            group_id = request.POST.get('group_id')
            student_id = request.POST.get('student_id')
            if group_id and student_id:
                group = AssignmentGroup.objects.get(pk=group_id, assignment=assignment)
                student = Student.objects.get(pk=student_id)
                group.members.add(student)
                messages.success(request, f'Added {student.reg_number} to {group.name}')
        
        elif action == 'set_leader':
            group_id = request.POST.get('group_id')
            student_id = request.POST.get('student_id')
            if group_id and student_id:
                group = AssignmentGroup.objects.get(pk=group_id, assignment=assignment)
                student = Student.objects.get(pk=student_id)
                if group.members.filter(pk=student.pk).exists():
                    group.leader = student
                    group.save()
                    messages.success(request, f'{student.reg_number} is now leader of {group.name}')
                else:
                    messages.error(request, 'Student must be a member first')
        
        elif action == 'remove_member':
            group_id = request.POST.get('group_id')
            student_id = request.POST.get('student_id')
            if group_id and student_id:
                group = AssignmentGroup.objects.get(pk=group_id, assignment=assignment)
                student = Student.objects.get(pk=student_id)
                group.members.remove(student)
                if group.leader_id == student.id:
                    group.leader = None
                    group.save()
                messages.success(request, f'Removed {student.reg_number} from {group.name}')
        
        return redirect('lecturers:assignment_groups', pk=pk)
    
    return render(request, 'lecturers/assignment_groups.html', {
        'assignment': assignment,
        'groups': assignment.groups.all().prefetch_related('members', 'leader'),
        'students': registered_students,
    })


@login_required
def assignment_submissions(request, pk):
    """View all submissions for an assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)
    
    user = request.user
    if not (user.is_superuser or (assignment.created_by and assignment.created_by.user_id == user.id)):
        return HttpResponseForbidden('Permission denied')
    
    individual_subs = assignment.individual_submissions.select_related('student__user').order_by('-submitted_at')
    group_subs = GroupSubmission.objects.filter(group__assignment=assignment).select_related('group', 'submitted_by__user').order_by('-submitted_at')
    
    return render(request, 'lecturers/assignment_submissions.html', {
        'assignment': assignment,
        'individual_subs': individual_subs,
        'group_subs': group_subs,
    })


@login_required
def grade_individual(request, pk):
    """Grade an individual submission"""
    submission = get_object_or_404(IndividualSubmission, pk=pk)
    assignment = submission.assignment
    
    user = request.user
    if not (user.is_superuser or (assignment.created_by and assignment.created_by.user_id == user.id)):
        return HttpResponseForbidden('Permission denied')
    
    lecturer = Lecturer.objects.filter(user=user).first()
    
    if request.method == 'POST':
        score = request.POST.get('score')
        feedback = request.POST.get('feedback', '').strip()
        
        try:
            score = float(score)
            if 0 <= score <= assignment.max_individual_mark:
                submission.score = score
                submission.feedback = feedback
                submission.graded_by = lecturer
                submission.graded_at = timezone.now()
                submission.save()
                messages.success(request, f'Graded: {submission.student.reg_number} = {score}/{assignment.max_individual_mark}')
                return redirect('lecturers:assignment_submissions', pk=assignment.pk)
            else:
                messages.error(request, f'Score must be 0-{assignment.max_individual_mark}')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid score')
    
    return render(request, 'lecturers/grade_submission.html', {
        'submission': submission,
        'assignment': assignment,
        'is_group': False,
    })


@login_required
def grade_group(request, pk):
    """Grade a group submission - applies to all members"""
    submission = get_object_or_404(GroupSubmission, pk=pk)
    assignment = submission.group.assignment
    
    user = request.user
    if not (user.is_superuser or (assignment.created_by and assignment.created_by.user_id == user.id)):
        return HttpResponseForbidden('Permission denied')
    
    lecturer = Lecturer.objects.filter(user=user).first()
    
    if request.method == 'POST':
        score = request.POST.get('score')
        feedback = request.POST.get('feedback', '').strip()
        
        try:
            score = float(score)
            if 0 <= score <= assignment.max_group_mark:
                submission.score = score
                submission.feedback = feedback
                submission.graded_by = lecturer
                submission.graded_at = timezone.now()
                submission.save()
                messages.success(request, f'Graded {submission.group.name}: {score}/{assignment.max_group_mark}')
                return redirect('lecturers:assignment_submissions', pk=assignment.pk)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid score')
    
    return render(request, 'lecturers/grade_submission.html', {
        'submission': submission,
        'assignment': assignment,
        'is_group': True,
    })


# ============ STUDENT-SIDE VIEWS ============

@login_required
def student_assignment_list(request):
    """Students see assignments for courses they registered for"""
    from students.models import Student
    
    student = Student.objects.filter(user=request.user).first()
    if not student:
        return HttpResponseForbidden('Student profile not found')
    
    # Get courses registered by student
    from students.models import CourseRegistration
    reg_courses = CourseRegistration.objects.filter(student=student).values_list('course_id', flat=True)
    
    assignments = Assignment.objects.filter(
        course_id__in=reg_courses,
        is_published=True
    ).select_related('course').order_by('-created_at')
    
    # Annotate with submission status
    assignment_data = []
    for a in assignments:
        ind_sub = IndividualSubmission.objects.filter(assignment=a, student=student).first()
        my_group = a.groups.filter(members=student).first()
        grp_sub = GroupSubmission.objects.filter(group=my_group).first() if my_group else None
        
        assignment_data.append({
            'assignment': a,
            'individual_submitted': ind_sub is not None,
            'individual_score': ind_sub.score if ind_sub else None,
            'my_group': my_group,
            'is_leader': my_group and my_group.leader_id == student.id,
            'group_submitted': grp_sub is not None,
            'group_score': grp_sub.score if grp_sub else None,
        })
    
    return render(request, 'lecturers/student_assignment_list.html', {
        'assignment_data': assignment_data,
        'student': student,
    })


@login_required
def student_assignment_detail(request, pk):
    """Student views assignment and submits"""
    from students.models import Student
    
    student = Student.objects.filter(user=request.user).first()
    if not student:
        return HttpResponseForbidden('Student profile not found')
    
    assignment = get_object_or_404(Assignment, pk=pk, is_published=True)
    
    # Get student's submission status
    ind_sub = IndividualSubmission.objects.filter(assignment=assignment, student=student).first()
    my_group = assignment.groups.filter(members=student).first()
    is_leader = my_group and my_group.leader_id == student.id
    grp_sub = GroupSubmission.objects.filter(group=my_group).first() if my_group else None
    
    if request.method == 'POST':
        submission_type = request.POST.get('submission_type')
        content_text = request.POST.get('content_text', '').strip()
        content_file = request.FILES.get('content_file')
        
        if not content_text and not content_file:
            messages.error(request, 'Please provide text or upload a file')
        elif submission_type == 'individual':
            if ind_sub:
                messages.error(request, 'You already submitted the individual part')
            else:
                IndividualSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    content_text=content_text,
                    content_file=content_file
                )
                messages.success(request, 'Individual submission received!')
                return redirect('lecturers:student_assignment_detail', pk=pk)
        elif submission_type == 'group':
            if not is_leader:
                messages.error(request, 'Only the group leader can submit')
            elif grp_sub:
                messages.error(request, 'Group already submitted')
            else:
                GroupSubmission.objects.create(
                    group=my_group,
                    submitted_by=student,
                    content_text=content_text,
                    content_file=content_file
                )
                messages.success(request, f'Group submission received for {my_group.name}!')
                return redirect('lecturers:student_assignment_detail', pk=pk)
    
    return render(request, 'lecturers/student_assignment_detail.html', {
        'assignment': assignment,
        'student': student,
        'ind_sub': ind_sub,
        'my_group': my_group,
        'is_leader': is_leader,
        'grp_sub': grp_sub,
        'now': timezone.now(),
    })
