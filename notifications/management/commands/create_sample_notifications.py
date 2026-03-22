from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import Notification
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample notifications for testing'

    def handle(self, *args, **options):
        # Get admin user as sender
        try:
            admin_user = User.objects.filter(user_type='admin').first()
            if not admin_user:
                self.stdout.write(self.style.ERROR('No admin user found. Please create an admin user first.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error finding admin user: {e}'))
            return

        # Get teacher users as recipients
        teachers = User.objects.filter(user_type='teacher')
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('No teacher users found. Please create teacher users first.'))
            return

        # Sample notifications data
        notifications_data = [
            {
                'title': 'New Assignment Deadline',
                'message': 'Please remind students that the Programming Fundamentals assignment is due next Friday. Make sure to check submission quality and provide feedback.',
                'notification_type': 'academic',
                'priority': 'high',
            },
            {
                'title': 'Faculty Meeting Tomorrow',
                'message': 'There will be a faculty meeting tomorrow at 2:00 PM in the conference room. We will discuss the upcoming semester schedule and new curriculum changes.',
                'notification_type': 'general',
                'priority': 'medium',
            },
            {
                'title': 'Attendance Report Due',
                'message': 'Monthly attendance reports are due by the end of this week. Please ensure all attendance records are up to date in the system.',
                'notification_type': 'attendance',
                'priority': 'medium',
            },
            {
                'title': 'Exam Schedule Released',
                'message': 'The mid-semester exam schedule has been released. Please check your assigned exam slots and prepare accordingly.',
                'notification_type': 'exam',
                'priority': 'high',
            },
            {
                'title': 'System Maintenance Notice',
                'message': 'The student management system will undergo maintenance this Sunday from 2:00 AM to 6:00 AM. Please plan your activities accordingly.',
                'notification_type': 'general',
                'priority': 'low',
            },
        ]

        created_count = 0
        
        for notification_data in notifications_data:
            try:
                # Create notification
                notification = Notification.objects.create(
                    title=notification_data['title'],
                    message=notification_data['message'],
                    notification_type=notification_data['notification_type'],
                    priority=notification_data['priority'],
                    sender=admin_user,
                    send_email=False
                )
                
                # Add all teachers as recipients
                notification.recipients.set(teachers)
                created_count += 1
                
                self.stdout.write(f'Created notification: {notification.title}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating notification "{notification_data["title"]}": {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} sample notifications for {teachers.count()} teachers.'
            )
        )