def notifications_context(request):
    """Injects unread_count and recent_notifications into every template."""
    if not request.user.is_authenticated:
        return {}

    user = request.user

    # Deadline check for students (lightweight, runs on every page)
    if user.role == 'student':
        try:
            from .utils import check_deadlines
            check_deadlines(user.student)
        except Exception:
            pass

    qs = user.notifications.all()
    unread_count        = qs.filter(is_read=False).count()
    recent_notifications = qs[:12]

    return {
        'unread_count':         unread_count,
        'recent_notifications': recent_notifications,
    }
