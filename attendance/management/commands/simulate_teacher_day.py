from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog
from datetime import datetime, time, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Simulate a full day of teacher activities for real-time tracking demo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--teacher-id',
            type=int,
            help='Specific teacher ID to simulate (optional)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Simulating a full day of teacher activities...'))
        
        # Get teacher
        if options['teacher_id']:
            try:
                teacher_user = User.objects.get(id=options['teacher_id'], user_type='teacher')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Teacher with ID {options["teacher_id"]} not found.'))
                return
        else:
            teacher_user = User.objects.filter(user_type='teacher').first()
            if not teacher_user:
                self.stdout.write(self.style.ERROR('No teacher users found. Please create a teacher first.'))
                return
        
        teacher = teacher_user.teacher_profile
        today = timezone.now().date()
        
        self.stdout.write(f'Simulating day for teacher: {teacher.user.get_full_name()}')
        
        # Clear existing activities for today to start fresh
        TeacherActivityLog.objects.filter(teacher=teacher, timestamp__date=today).delete()
        TeacherAttendance.objects.filter(teacher=teacher, date=today).delete()
        
        # Define activities throughout the day
        base_time = timezone.now().replace(hour=8, minute=45, second=0, microsecond=0)
        
        activities = [
            (base_time, 'first_login', 'FIRST ACTIVITY: Teacher logged in to system'),
            (base_time + timedelta(minutes=5), 'dashboard_access', 'Accessed teacher dashboard'),
            (base_time + timedelta(minutes=15), 'mark_attendance', 'Marked attendance for Mathematics - Class 10A'),
            (base_time + timedelta(hours=1), 'mark_attendance', 'Marked attendance for Physics - Class 10B'),
            (base_time + timedelta(hours=1, minutes=30), 'create_assignment', 'Created assignment for Mathematics'),
            (base_time + timedelta(hours=2, minutes=15), 'mark_attendance', 'Marked attendance for Chemistry - Class 11A'),
            (base_time + timedelta(hours=3), 'grade_exam', 'Graded physics exam papers'),
            (base_time + timedelta(hours=4), 'send_message', 'Sent message to parent about student progress'),
            (base_time + timedelta(hours=5), 'view_report', 'Viewed student attendance reports'),
            (base_time + timedelta(hours=6, minutes=30), 'system_navigation', 'Final system check before leaving'),
        ]
        
        # Create attendance record
        first_activity_time = activities[0][0]
        last_activity_time = activities[-1][0]
        
        attendance = TeacherAttendance.objects.create(
            teacher=teacher,
            date=today,
            first_activity_time=first_activity_time,
            last_activity_time=last_activity_time,
            check_in_time=first_activity_time.time(),
            check_out_time=last_activity_time.time(),
            is_auto_marked=True
        )
        
        # Create activity logs
        for activity_time, activity_type, description in activities:
            TeacherActivityLog.objects.create(
                teacher=teacher,
                activity_type=activity_type,
                description=description,
                timestamp=activity_time,
                ip_address='127.0.0.1'
            )
        
        # Calculate hours and determine status
        attendance.calculate_hours()
        attendance.determine_status_advanced()
        attendance.save()
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Simulated full day attendance:'))
        self.stdout.write(f'  - Teacher: {teacher.user.get_full_name()}')
        self.stdout.write(f'  - Date: {attendance.date}')
        self.stdout.write(f'  - Status: {attendance.get_status_display()}')
        self.stdout.write(f'  - First Activity: {attendance.first_activity_time.strftime("%H:%M:%S")}')
        self.stdout.write(f'  - Last Activity: {attendance.last_activity_time.strftime("%H:%M:%S")}')
        self.stdout.write(f'  - Total Hours: {attendance.total_hours}')
        self.stdout.write(f'  - Has Real Activities: {attendance.has_performed_duties()}')
        
        # Show all activities
        all_activities = TeacherActivityLog.objects.filter(
            teacher=teacher,
            timestamp__date=today
        ).order_by('timestamp')
        
        self.stdout.write(f'\n✓ All activities for {teacher.user.get_full_name()} today:')
        for activity in all_activities:
            self.stdout.write(f'  - {activity.timestamp.strftime("%H:%M:%S")}: {activity.get_activity_type_display()} - {activity.description}')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Full day simulation completed!'))
        self.stdout.write('Check the Teacher Attendance Dashboard to see the real-time activity tracking in action.')
        self.stdout.write(f'Server URL: http://127.0.0.1:8075/attendance/teacher-dashboard/')
