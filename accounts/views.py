from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if hasattr(user, 'must_change_password') and user.must_change_password:
        return redirect('change_password')

    role = getattr(user, 'role', 'admin')

    if role == 'student':
        return redirect('student_dashboard')
    elif role == 'lecturer':
        return redirect('lecturers:dashboard')
    elif role == 'registrar':
        return redirect('registrar_dashboard')
    elif role == 'bursar':
        return redirect('admin:index')
    elif role in ['admin', 'academic_officer']:
        return redirect('admin:index')
    return redirect('admin:index')

@login_required
def change_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if new_password != confirm:
            messages.error(request, 'Passwords do not match.')
        elif len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            request.user.set_password(new_password)
            if hasattr(request.user, 'must_change_password'):
                request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully. Welcome!')
            return redirect('dashboard')
    return render(request, 'accounts/change_password.html')
