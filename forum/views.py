from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import ForumPost, ForumReply
from academics.models import Course
from core.models import Semester


def get_user_courses(user):
    if user.role == 'lecturer':
        from lecturers.models import Lecturer, LecturerCourse
        try:
            lect = Lecturer.objects.get(user=user)
            ids  = LecturerCourse.objects.filter(lecturer=lect, is_active=True).values_list('course_id', flat=True)
            return Course.objects.filter(id__in=ids).order_by('code')
        except Exception:
            return Course.objects.none()
    elif user.role == 'student':
        from students.models import Student
        from academics.models import CourseRegistration
        try:
            student = Student.objects.get(user=user)
            ids = CourseRegistration.objects.filter(
                student=student, status__in=['registered', 'carryover']
            ).values_list('course_id', flat=True)
            return Course.objects.filter(id__in=set(ids)).order_by('code')
        except Exception:
            return Course.objects.none()
    return Course.objects.all().order_by('code')


# ─── HOME ──────────────────────────────────────────────────────────────────────

@login_required
def forum_home(request):
    courses      = get_user_courses(request.user)
    course_data  = []
    for course in courses:
        posts  = ForumPost.objects.filter(course=course)
        latest = posts.order_by('-created_at').first()
        course_data.append({
            'course':       course,
            'post_count':   posts.count(),
            'latest_post':  latest,
        })
    return render(request, 'forum/home.html', {'course_data': course_data})


# ─── COURSE FORUM ──────────────────────────────────────────────────────────────

@login_required
def forum_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    posts  = ForumPost.objects.filter(course=course).select_related('author').prefetch_related('likes', 'replies')
    return render(request, 'forum/course_forum.html', {
        'course':       course,
        'posts':        posts,
        'is_lecturer':  request.user.role == 'lecturer',
    })


# ─── POST DETAIL + REPLY ───────────────────────────────────────────────────────

@login_required
def post_detail(request, post_id):
    post    = get_object_or_404(ForumPost, id=post_id)
    replies = post.replies.select_related('author').prefetch_related('likes')

    if request.method == 'POST':
        content    = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')
        if content:
            ForumReply.objects.create(
                post=post, author=request.user,
                content=content,
                attachment=attachment or None,
            )
            messages.success(request, 'Reply posted!')
            try:
                from notifications.utils import notify
                if post.author != request.user:
                    notify(
                        recipient=post.author,
                        ntype='forum_reply',
                        title=f'🗨️ New reply on: {post.title}',
                        message=f'{request.user.get_full_name()} replied to your post',
                        link=f'/forum/post/{post.id}/',
                    )
            except Exception:
                pass
        else:
            messages.error(request, 'Reply cannot be empty.')
        return redirect('forum:post_detail', post_id=post_id)

    liked_reply_ids = list(request.user.liked_replies.values_list('id', flat=True))
    return render(request, 'forum/post_detail.html', {
        'post':            post,
        'replies':         replies,
        'is_lecturer':     request.user.role == 'lecturer',
        'user_liked_post': post.likes.filter(id=request.user.id).exists(),
        'liked_reply_ids': liked_reply_ids,
    })


# ─── CREATE POST ───────────────────────────────────────────────────────────────

@login_required
def post_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        content    = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')
        semester   = Semester.objects.filter(is_active=True).first()

        if title and content:
            post = ForumPost.objects.create(
                course=course, semester=semester,
                author=request.user,
                title=title, content=content,
                attachment=attachment or None,
            )
            messages.success(request, 'Post created!')
            return redirect('forum:post_detail', post_id=post.id)
        messages.error(request, 'Title and content are required.')

    return render(request, 'forum/post_create.html', {'course': course})


# ─── LIKES ─────────────────────────────────────────────────────────────────────

@login_required
def post_like(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def reply_like(request, reply_id):
    reply = get_object_or_404(ForumReply, id=reply_id)
    if reply.likes.filter(id=request.user.id).exists():
        reply.likes.remove(request.user)
    else:
        reply.likes.add(request.user)
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ─── PIN ───────────────────────────────────────────────────────────────────────

@login_required
def post_pin(request, post_id):
    if request.user.role != 'lecturer':
        messages.error(request, 'Only lecturers can pin posts.')
        return redirect('forum:post_detail', post_id=post_id)
    post          = get_object_or_404(ForumPost, id=post_id)
    post.is_pinned = not post.is_pinned
    post.save()
    messages.success(request, f'Post {"📌 pinned" if post.is_pinned else "unpinned"}.')
    return redirect('forum:post_detail', post_id=post_id)


# ─── DELETE ────────────────────────────────────────────────────────────────────

@login_required
def post_delete(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    if post.author != request.user and request.user.role not in ('lecturer', 'admin'):
        messages.error(request, 'Permission denied.')
        return redirect('forum:post_detail', post_id=post_id)
    course_id = post.course.id
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
        return redirect('forum:forum_course', course_id=course_id)
    return render(request, 'forum/delete_confirm.html', {'item': post, 'item_type': 'post', 'back_url': f'/forum/course/{course_id}/'})


@login_required
def reply_delete(request, reply_id):
    reply = get_object_or_404(ForumReply, id=reply_id)
    if reply.author != request.user and request.user.role not in ('lecturer', 'admin'):
        messages.error(request, 'Permission denied.')
        return redirect('forum:post_detail', post_id=reply.post.id)
    post_id = reply.post.id
    reply.delete()
    messages.success(request, 'Reply deleted.')
    return redirect('forum:post_detail', post_id=post_id)
