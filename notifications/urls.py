from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('create/', views.create_notification, name='create_notification'),
    path('mark-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),
    path('api/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='get_recent_notifications'),
]

