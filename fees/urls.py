from django.urls import path
from . import views

urlpatterns = [
    path('pay/', views.make_payment, name='make_payment'),
    path('my/', views.my_payments, name='my_payments'),
    path('bursar/', views.bursar_dashboard, name='bursar_dashboard'),
    path('approve/<int:pk>/', views.approve_payment, name='approve_payment'),
    path('reject/<int:pk>/', views.reject_payment, name='reject_payment'),
]
path('receipt/<int:payment_id>/pdf/', views.download_fee_receipt, name='download_fee_receipt'),