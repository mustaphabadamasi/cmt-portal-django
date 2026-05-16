from django.shortcuts import render

# Create your views here.

def offline(request):
    """Offline fallback page for PWA"""
    return render(request, 'core/offline.html')

