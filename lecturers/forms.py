from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Lecturer, LecturerCourse

User = get_user_model()


class LecturerCreateForm(forms.Form):
    """Registrar uses this to create a lecturer User + profile in one step."""

    username   = forms.CharField(max_length=150, help_text="Used to log in. Letters, digits, and @/./+/-/_ only.")
    first_name = forms.CharField(max_length=150)
    last_name  = forms.CharField(max_length=150)
    email      = forms.EmailField(required=False)

    staff_id      = forms.CharField(max_length=30)
    title         = forms.ChoiceField(choices=[('', '---')] + Lecturer.TITLE_CHOICES, required=False)
    gender        = forms.ChoiceField(choices=[('', '---')] + Lecturer.GENDER_CHOICES, required=False)
    phone         = forms.CharField(max_length=20, required=False)
    department    = forms.CharField(max_length=120, required=False)
    date_employed = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    photo         = forms.ImageField(required=False)

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("That username is already taken.")
        return u

    def clean_staff_id(self):
        sid = self.cleaned_data['staff_id'].strip()
        if Lecturer.objects.filter(staff_id=sid).exists():
            raise forms.ValidationError("A lecturer with that staff ID already exists.")
        return sid

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        user = User.objects.create_user(
            username=d['username'],
            password=d['staff_id'],
            first_name=d['first_name'],
            last_name=d['last_name'],
            email=d.get('email') or '',
        )
        user.role = 'lecturer'
        user.must_change_password = True
        user.save(update_fields=['role', 'must_change_password'])

        return Lecturer.objects.create(
            user=user,
            staff_id=d['staff_id'],
            title=d.get('title') or '',
            gender=d.get('gender') or '',
            phone=d.get('phone') or '',
            department=d.get('department') or '',
            date_employed=d.get('date_employed'),
            photo=d.get('photo'),
        )


class LecturerUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name  = forms.CharField(max_length=150)
    email      = forms.EmailField(required=False)

    class Meta:
        model = Lecturer
        fields = ['staff_id', 'title', 'gender', 'phone', 'department',
                  'date_employed', 'photo', 'status']
        widgets = {'date_employed': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial  = self.instance.user.last_name
            self.fields['email'].initial      = self.instance.user.email

    @transaction.atomic
    def save(self, commit=True):
        lecturer = super().save(commit=False)
        u = lecturer.user
        u.first_name = self.cleaned_data['first_name']
        u.last_name  = self.cleaned_data['last_name']
        u.email      = self.cleaned_data.get('email') or ''
        if commit:
            u.save()
            lecturer.save()
        return lecturer


class LecturerCourseAssignmentForm(forms.ModelForm):
    class Meta:
        model = LecturerCourse
        fields = ['course', 'semester', 'notes']

# ============================================================
# Phase 1B — Quiz forms
# ============================================================
from .models import Quiz, Question, Choice


class QuizForm(forms.ModelForm):
    """Course/Semester dropdowns are filtered to the lecturer's active assignments."""

    class Meta:
        model = Quiz
        fields = ['course', 'semester', 'title', 'description',
                  'max_score', 'questions_to_attempt', 'time_limit_minutes',
                  'available_from', 'available_until']
        widgets = {
            'description':     forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional instructions shown to students before they start.'}),
            'available_from':  forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, lecturer=None, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing instance, datetime-local widget needs ISO format
        for f in ('available_from', 'available_until'):
            if self.instance and getattr(self.instance, f, None):
                self.initial[f] = getattr(self.instance, f).strftime('%Y-%m-%dT%H:%M')
        if lecturer is not None:
            from .models import LecturerCourse
            qs = LecturerCourse.objects.filter(lecturer=lecturer, is_active=True)
            self.fields['course'].queryset   = self.fields['course'].queryset.filter(id__in=qs.values_list('course_id', flat=True))
            self.fields['semester'].queryset = self.fields['semester'].queryset.filter(id__in=qs.values_list('semester_id', flat=True))

    def clean(self):
        cleaned = super().clean()
        af, au = cleaned.get('available_from'), cleaned.get('available_until')
        if af and au and au <= af:
            raise forms.ValidationError("'Available until' must be after 'Available from'.")
        return cleaned


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'points']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Question text...'})}


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text']
        widgets = {'text': forms.TextInput(attrs={'placeholder': 'Option text...'})}

