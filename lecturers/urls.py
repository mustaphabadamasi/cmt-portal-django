from django.urls import path
from . import views

app_name = 'lecturers'

urlpatterns = [
    path('',                              views.lecturer_list,         name='list'),
    path('new/',                          views.lecturer_create,       name='create'),
    path('<int:pk>/',                     views.lecturer_detail,       name='detail'),
    path('<int:pk>/edit/',                views.lecturer_update,       name='update'),
    path('<int:pk>/assign/',              views.assign_course,         name='assign'),
    path('<int:pk>/reset-password/',      views.reset_password,        name='reset_password'),
    path('assignment/<int:pk>/toggle/',   views.toggle_assignment,     name='toggle_assignment'),
    path('assignment/<int:pk>/delete/',   views.delete_assignment,     name='delete_assignment'),
    path('dashboard/',  views.lecturer_dashboard, name='dashboard'),
    path('my-courses/', views.my_courses,         name='my_courses'),

    path('quizzes/',                       views.quiz_list,           name='quiz_list'),
    path('quizzes/new/',                   views.quiz_create,         name='quiz_create'),
    path('quizzes/<int:pk>/',              views.quiz_detail,         name='quiz_detail'),
    path('quizzes/<int:pk>/edit/',         views.quiz_update,         name='quiz_update'),
    path('quizzes/<int:pk>/import/',       views.quiz_import_csv,     name='quiz_import'),
    path('quizzes/<int:pk>/delete/',       views.quiz_delete,         name='quiz_delete'),
    path('quizzes/<int:pk>/publish/',      views.quiz_publish,        name='quiz_publish'),
    path('quizzes/<int:pk>/question/add/', views.question_create,     name='question_create'),
    path('questions/<int:pk>/delete/',     views.question_delete,     name='question_delete'),
    path('questions/<int:pk>/choice/add/', views.choice_create,       name='choice_create'),
    path('choices/<int:pk>/delete/',       views.choice_delete,       name='choice_delete'),
    path('choices/<int:pk>/correct/',      views.choice_mark_correct, name='choice_mark_correct'),

    path('student/quizzes/',                  views.student_quiz_list,    name='student_quiz_list'),
    path('student/quizzes/<int:pk>/start/',   views.quiz_start,           name='quiz_start'),
    path('attempts/<int:pk>/take/',           views.quiz_take,            name='quiz_take'),
    path('attempts/<int:pk>/result/',         views.quiz_attempt_result,  name='quiz_attempt_result'),

    path('quizzes/<int:pk>/attempts/',                            views.quiz_attempts,   name='quiz_attempts'),
    path('attempts/<int:pk>/inspect/',                            views.attempt_inspect, name='attempt_inspect'),
    path('course-results/<int:course_id>/<int:semester_id>/',     views.course_results,  name='course_results'),

    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:pk>/groups/', views.assignment_groups, name='assignment_groups'),
    path('assignments/<int:pk>/submissions/', views.assignment_submissions, name='assignment_submissions'),
    path('submissions/individual/<int:pk>/grade/', views.grade_individual, name='grade_individual'),
    path('submissions/group/<int:pk>/grade/', views.grade_group, name='grade_group'),
    path('my-assignments/', views.student_assignment_list, name='student_assignment_list'),
    path('my-assignments/<int:pk>/', views.student_assignment_detail, name='student_assignment_detail'),
]