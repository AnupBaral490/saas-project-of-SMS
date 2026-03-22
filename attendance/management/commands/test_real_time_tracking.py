from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog
from datetime import datetime, time

User = get_user_model()

class Command(BaseCommand):
    help = 'Test real-time activity tracking for teachers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing real-time activity tracking...'))
        
        # Get a teacher user
        try:
            teacher_user = User.objects.filter(user_type='teacher').first()
            if not teacher_user:
                self.stdout.write(self.style.ERROR('No teacher users found. Please create a teacher first.'))
                return
            
            teacher = teacher_user.teacher_profile
            today = timezone.now().date()
            
            self.stdout.write(f'Testing with teacher: {teacher.user.get_full_name()}')
            
            # Simulate first activity (login)
            first_activity_time = timezone.now()
            TeacherActivityLog.objects.create(
                teacher=teacher,
                activity_type='first_login',
                description='FIRST ACTIVITY: Teacher logged in to system',
                ip_address='127.0.0.1'
            )
            
            # Get or create attendance record
            attendance, created = TeacherAttendance.objects.get_or_create(
                teacher=teacher,
                date=today,
                defaults={
                    'first_activity_time': first_activity_time,
                    'check_in_time': first_activity_time.time(),
                    'is_auto_marked': True,
                    'status': 'present'
                }
            )
            
            if not created:
                # Update existing record
                if not attendance.first_activity_time:
                    attendance.first_activity_time = first_activity_time
                    attendance.check_in_time = first_activity_time.time()
            
            # Simulate marking attendance activity
            mark_attendance_time = timezone.now()
            TeacherActivityLog.objects.create(
                teacher=teacher,
                activity_type='mark_attendance',
                description='Marked student attendance for Mathematics - Class 10A',
                ip_address='127.0.0.1'
            )
            
            # Update last activity time
            attendance.last_activity_time = mark_attendance_time
            attendance.check_out_time = mark_attendance_time.time()
            
            # Calculate hours and determine status
            attendance.calculate_hours()
            attendance.determine_status_advanced()
            attendance.save()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Created attendance record:'))
            self.stdout.write(f'  - Teacher: {teacher.user.get_full_name()}')
            self.stdout.write(f'  - Date: {attendance.date}')
            self.stdout.write(f'  - Status: {attendance.get_status_display()}')
            self.stdout.write(f'  - First Activity: {attendance.first_activity_time}')
            self.stdout.write(f'  - Last Activity: {attendance.last_activity_time}')
            self.stdout.write(f'  - Check In: {attendance.check_in_time}')
            self.stdout.write(f'  - Check Out: {attendance.check_out_time}')
            self.stdout.write(f'  - Total Hours: {attendance.total_hours}')
            self.stdout.write(f'  - Has Real Activities: {attendance.has_performed_duties()}')
            
            # Show recent activities
            recent_activities = TeacherActivityLog.objects.filter(
                teacher=teacher,
                timestamp__date=today
            ).order_by('-timestamp')[:5]
            
            self.stdout.write(f'\n✓ Recent activities for {teacher.user.get_full_name()}:')
            for activity in recent_activities:
                self.stdout.write(f'  - {activity.timestamp.strftime("%H:%M:%S")}: {activity.get_activity_type_display()} - {activity.description}')
            
            self.stdout.write(self.style.SUCCESS('\n✓ Real-time tracking test completed successfully!'))
            self.stdout.write('You can now check the Teacher Attendance Dashboard to see the real activity times.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during test: {str(e)}'))
