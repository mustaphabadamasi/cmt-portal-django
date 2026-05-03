from django.urls import path
from . import views

urlpatterns = [
    path('exam-card/<int:student_id>/', views.exam_card, name='exam_card'),
    path('course-reg/<int:student_id>/', views.course_reg_form, name='course_reg_form'),
    path('receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt'),
]