from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", lambda r: redirect("login"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("students/", include("students.urls")),
    path('lecturers/', include('lecturers.urls')),
    path('results/', include('results.urls', namespace='results')),
    path('admissions/', include('admissions.urls', namespace='admissions')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('forum/', include('forum.urls', namespace='forum')),
    path('live-classes/', include('live_classes.urls', namespace='live_classes')),
    path("registrar/", include("registrar.urls")),
    path("fees/", include("fees.urls")),
    path("documents/", include("documents.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
