from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from .models import Notification, NotificationRead
from .forms import NotificationForm, QuickNotificationForm
from accounts.models import User

def can_send_notifications(user):
    return user.is_authenticated and user.user_type in ['admin', 'teacher']

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipients=request.user).order_by('-created_at')
    
    # Mark notifications as read when viewed
    unread_notifications = notifications.exclude(
        notificationread__user=request.user
    )
    
    for notification in unread_notifications:
        NotificationRead.objects.get_or_create(
            notification=notification,
            user=request.user
        )
    
    context = {
        'notifications': notifications,
        'unread_count': unread_notifications.count()
    }
    
    return render(request, 'notifications/notification_list.html', context)

@login_required
@user_passes_test(can_send_notifications)
def create_notification(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'detailed')
        
        if form_type == 'quick':
            form = QuickNotificationForm(request.POST)
            if form.is_valid():
                # Get recipients based on group selection
                recipient_group = form.cleaned_data['recipient_group']
                
                if recipient_group == 'all_students':
                    recipients = User.objects.filter(user_type='student')
                elif recipient_group == 'all_teachers':
                    recipients = User.objects.filter(user_type='teacher')
                elif recipient_group == 'all_parents':
                    recipients = User.objects.filter(user_type='parent')
                elif recipient_group == 'all_users':
                    recipients = User.objects.exclude(user_type='admin')
                else:
                    recipients = User.objects.none()
                
                # Create notification
                notification = Notification.objects.create(
                    title=form.cleaned_data['title'],
                    message=form.cleaned_data['message'],
                    notification_type=form.cleaned_data['notification_type'],
                    priority=form.cleaned_data['priority'],
                    sender=request.user,
                    send_email=form.cleaned_data['send_email']
                )
                
                # Add recipients
                notification.recipients.set(recipients)
                
                messages.success(
                    request, 
                    f'Notification sent successfully to {recipients.count()} users!'
                )
                return redirect('notifications:notification_list')
        else:
            form = NotificationForm(request.POST, user=request.user)
            if form.is_valid():
                notification = form.save(commit=False)
                notification.sender = request.user
                notification.save()
                form.save_m2m()  # Save many-to-many relationships
                
                messages.success(
                    request, 
                    f'Notification sent successfully to {notification.recipients.count()} users!'
                )
                return redirect('notifications:notification_list')
    else:
        form = NotificationForm(user=request.user)
        quick_form = QuickNotificationForm()
    
    context = {
        'form': form if request.method == 'GET' or request.POST.get('form_type') != 'quick' else NotificationForm(user=request.user),
        'quick_form': quick_form if request.method == 'GET' or request.POST.get('form_type') == 'quick' else QuickNotificationForm()
    }
    
    return render(request, 'notifications/create_notification.html', context)

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipients=request.user)
    
    NotificationRead.objects.get_or_create(
        notification=notification,
        user=request.user
    )
    
    messages.success(request, 'Notification marked as read.')
    return redirect('notifications:notification_list')

@login_required
def get_unread_count(request):
    """API endpoint to get unread notification count for current user"""
    unread_count = Notification.objects.filter(
        recipients=request.user
    ).exclude(
        notificationread__user=request.user
    ).count()
    
    return JsonResponse({'unread_count': unread_count})

@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications for dropdown"""
    notifications = Notification.objects.filter(
        recipients=request.user
    ).order_by('-created_at')[:5]
    
    notifications_data = []
    for notification in notifications:
        is_read = NotificationRead.objects.filter(
            notification=notification,
            user=request.user
        ).exists()
        
        notifications_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'notification_type': notification.notification_type,
            'priority': notification.priority,
            'created_at': notification.created_at.strftime('%b %d, %Y %I:%M %p'),
            'is_read': is_read,
            'sender': notification.sender.get_full_name() or notification.sender.username
        })
    
    return JsonResponse({'notifications': notifications_data})