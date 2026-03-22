from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views, api_views, messaging_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    # API endpoints
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/logout/', api_views.api_logout, name='api_logout'),
    path('api/user-profile/', api_views.api_user_profile, name='api_user_profile'),
    path('api/teacher-dashboard-stats/', api_views.teacher_dashboard_stats, name='teacher_dashboard_stats'),
    # Admin-only user management
    path('admin/create-user/', views.admin_create_user, name='admin_create_user'),
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/users/<int:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/users/<int:user_id>/reset-password/', views.admin_reset_password, name='admin_reset_password'),
    # Parent-Teacher Messaging
    path('messages/', messaging_views.message_inbox, name='message_inbox'),
    path('messages/send/', messaging_views.send_message, name='send_message'),
    path('messages/send/<int:teacher_id>/', messaging_views.send_message, name='send_message_to_teacher'),
    path('messages/send/<int:teacher_id>/<int:student_id>/', messaging_views.send_message, name='send_message_about_student'),
    path('messages/<int:message_id>/', messaging_views.message_detail, name='message_detail'),
    path('contact-teachers/', messaging_views.contact_teachers, name='contact_teachers'),
]