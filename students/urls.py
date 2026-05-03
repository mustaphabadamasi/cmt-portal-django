from django.urls import path
from . import views

urlpatterns = [
    # Admin views
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/list/', views.student_list, name='student_list'),
    path('admin/add/', views.add_student, name='add_student'),
    path('admin/<int:pk>/', views.student_detail, name='student_detail'),
    path('admin/<int:pk>/delete/', views.delete_student, name='delete_student'),
    path('admin/migrate/', views.migrate_students, name='migrate_students'),

    # Student views
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('profile/', views.student_profile, name='student_profile'),
    path('photo/upload/', views.upload_photo, name='upload_photo'),
    path('courses/register/', views.register_courses, name='register_courses'),
    path('courses/my/', views.my_courses, name='my_courses'),
]
path('admin/semester-result/', views.semester_result, name='semester_result'),