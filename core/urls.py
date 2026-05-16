from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('offline/', views.offline, name='offline'),
]
