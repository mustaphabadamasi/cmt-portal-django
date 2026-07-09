from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    # Lecturer
    path('my-courses/',                    views.lecturer_result_courses, name='lecturer_courses'),
    path('enter/<int:course_id>/',         views.enter_results,           name='enter_results'),

    path('scoresheet/<int:course_id>/', views.download_scoresheet, name='scoresheet'),

    # Registrar
    path('registrar/',                     views.registrar_results,       name='registrar_results'),
    path('registrar/batch/<int:batch_id>/',views.registrar_batch_detail,  name='batch_detail'),
    path('registrar/batch/<int:batch_id>/approve/', views.approve_batch,  name='approve_batch'),
    path('registrar/batch/<int:batch_id>/reject/',  views.reject_batch,   name='reject_batch'),
    path('registrar/batch/<int:batch_id>/recall/', views.recall_batch, name='recall_batch'),
    path('registrar/batch/<int:batch_id>/senate-publish/', views.senate_publish, name='senate_publish'),
    path('registrar/batch/<int:batch_id>/senate-unpublish/', views.senate_unpublish, name='senate_unpublish'),
    path('registrar/batch/<int:batch_id>/senate-publish/', views.senate_publish, name='senate_publish'),
    path('registrar/batch/<int:batch_id>/senate-unpublish/', views.senate_unpublish, name='senate_unpublish'),

    # Student
    path('my-results/',                    views.student_results,         name='student_results'),
]