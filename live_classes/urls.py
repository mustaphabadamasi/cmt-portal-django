from django.urls import path
from . import views

app_name = 'live_classes'

urlpatterns = [
    # Lecturer
    path('lecturer/',                          views.lecturer_class_list,   name='lecturer_list'),
    path('lecturer/create/',                   views.lecturer_class_create, name='lecturer_create'),
    path('lecturer/<int:pk>/',                 views.lecturer_class_detail, name='lecturer_detail'),
    path('lecturer/<int:pk>/start/',           views.lecturer_class_start,  name='lecturer_start'),
    path('lecturer/<int:pk>/end/',             views.lecturer_class_end,    name='lecturer_end'),
    path('lecturer/<int:pk>/cancel/',          views.lecturer_class_cancel, name='lecturer_cancel'),
    path('lecturer/<int:pk>/delete/',          views.lecturer_class_delete, name='lecturer_delete'),

    # Student
    path('student/',                           views.student_class_list,    name='student_list'),
    path('student/<int:pk>/join/',             views.student_class_join,    name='student_join'),
    path('student/<int:pk>/leave/',            views.student_class_leave,   name='student_leave'),
]
