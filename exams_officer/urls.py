from django.urls import path
from . import views

app_name = 'exams_officer'

urlpatterns = [
    path('',                              views.dashboard,        name='dashboard'),
    path('exam-card/<int:student_id>/',   views.print_exam_card,  name='exam_card'),
    path('course-form/<int:student_id>/', views.print_course_form,name='course_form'),
    path('bulk-exam-cards/',              views.bulk_exam_cards,  name='bulk_exam_cards'),
    path('bulk-course-forms/',            views.bulk_course_forms,name='bulk_course_forms'),
]
