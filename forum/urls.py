from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('',                                views.forum_home,    name='forum_home'),
    path('course/<int:course_id>/',         views.forum_course,  name='forum_course'),
    path('course/<int:course_id>/new/',     views.post_create,   name='post_create'),
    path('post/<int:post_id>/',             views.post_detail,   name='post_detail'),
    path('post/<int:post_id>/like/',        views.post_like,     name='post_like'),
    path('post/<int:post_id>/pin/',         views.post_pin,      name='post_pin'),
    path('post/<int:post_id>/delete/',      views.post_delete,   name='post_delete'),
    path('reply/<int:reply_id>/like/',      views.reply_like,    name='reply_like'),
    path('reply/<int:reply_id>/delete/',    views.reply_delete,  name='reply_delete'),
]
