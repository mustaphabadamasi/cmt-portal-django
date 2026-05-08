from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="registrar_dashboard"),
    path("students/", views.students, name="registrar_students"),
    path("fees/", views.fees, name="registrar_fees"),
    path("documents/", views.documents, name="registrar_documents"),
    path("photo/", views.photo, name="registrar_photo"),
    path("photo/save/", views.save_photo, name="save_photo"),
    path("students/add/", views.add_student, name="registrar_add_student"),
    path("academic-config/", views.academic_config, name="academic_config"),
    path("academic-config/create-session/", views.create_session, name="create_session"),
    path("academic-config/session/<int:session_id>/toggle/", views.toggle_session, name="toggle_session"),
    path("academic-config/semester/<int:semester_id>/toggle/", views.toggle_semester, name="toggle_semester"),
    path("course-structure/", views.course_structure, name="course_structure"),
    path("course-structure/create/", views.create_outline, name="create_outline"),
    path("course-structure/<int:outline_id>/", views.edit_outline, name="edit_outline"),
    path("course-structure/<int:outline_id>/delete/", views.delete_outline, name="delete_outline"),
    path("payment/<int:payment_id>/approve/", views.approve_payment, name="registrar_approve_payment"),
    path("payment/<int:payment_id>/receipt/", views.payment_receipt, name="registrar_payment_receipt"),
]
