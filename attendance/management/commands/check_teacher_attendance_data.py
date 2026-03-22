from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from attendance.models import TeacherAttendance, TeacherActivityLog
from accounts.models import TeacherProfile

class Command(BaseCommand):
    help = 'Check teacher attendance data for debugging'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking Teacher Attendance Data...'))
        
        # Check teachers
        teachers = TeacherProfile.objects.all()
        self.stdout.write(f'Total Teachers: {teachers.count()}')
        
        for teacher in teachers:
            self.stdout.write(f'- {teacher.user.get_full_name()} ({teacher.user.username})')
        
        # Check today's attendance
        today = timezone.now().date()
        self.stdout.write(f'\nToday\'s Date: {today}')
        
        today_attendance = TeacherAttendance.objects.filter(date=today)
        self.stdout.write(f'Today\'s Attendance Records: {today_attendance.count()}')
        
        for attendance in today_attendance:
            self.stdout.write(f'- {attendance.teacher.user.get_full_name()}: {attendance.status}')
        
        # Check recent activity logs
        recent_activities = TeacherActivityLog.objects.filter(
            timestamp__date=today
        ).order_by('-timestamp')
        
        self.stdout.write(f'\nToday\'s Activity Logs: {recent_activities.count()}')
        
        for activity in recent_activities[:10]:
            self.stdout.write(f'- {activity.teacher.user.get_full_name()}: {activity.activity_type} at {activity.timestamp}')
        
        # Create sample data if none exists
        if teachers.count() > 0 and today_attendance.count() == 0:
            self.stdout.write('\nCreating sample attendance data...')
            
            for teacher in teachers:
                # Create attendance record
                attendance = TeacherAttendance.objects.create(
                    teacher=teacher,
                    date=today,
                    status='present',
                    check_in_time='09:00:00',
                    check_out_time='17:00:00',
                    total_hours=8.0,
                    is_auto_marked=False,
                    remarks='Sample data for testing'
                )
                
                # Create activity log
                TeacherActivityLog.objects.create(
                    teacher=teacher,
                    activity_type='login',
                    description='Sample login activity',
                    timestamp=timezone.now() - timedelta(hours=1)
                )
                
                TeacherActivityLog.objects.create(
                    teacher=teacher,
                    activity_type='mark_attendance',
                    description='Sample attendance marking',
                    timestamp=timezone.now() - timedelta(minutes=30)
                )
                
                self.stdout.write(f'Created sample data for {teacher.user.get_full_name()}')
        
        self.stdout.write(self.style.SUCCESS('\nData check completed!'))