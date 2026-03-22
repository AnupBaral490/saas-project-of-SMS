from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog
from datetime import datetime, time

User = get_user_model()

class Command(BaseCommand):
    help = 'Test teacher who logs in but performs no real duties (should be marked absent)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing inactive teacher scenario...'))
        
        # Get a teacher user
        try:
            teacher_users = User.objects.filter(user_type='teacher')
            if teacher_users.count() < 2:
                self.stdout.write(self.style.ERROR('Need at least 2 teachers for this test. Creating a second teacher...'))
                # Create a test teacher
                inactive_user = User.objects.create_user(
                    username='inactive_teacher',
                    email='inactive@school.com',
                    password='password123',
                    user_type='teacher',
                    first_name='Inactive',
                    last_name='Teacher'
                )
                TeacherProfile.objects.create(
                    user=inactive_user,
                    employee_id='EMP002',
                    department='Mathematics',
                    phone_number='9876543210'
                )
                teacher = inactive_user.teacher_profile
            else:
                # Use second teacher
                teacher = teacher_users[1].teacher_profile
            
            today = timezone.now().date()
            
            self.stdout.write(f'Testing with inactive teacher: {teacher.user.get_full_name()}')
            
            # Clear existing data for clean test
            TeacherActivityLog.objects.filter(teacher=teacher, timestamp__date=today).delete()
            TeacherAttendance.objects.filter(teacher=teacher, date=today).delete()
            
            # Simulate teacher who just logs in and browses but does no real work
            login_time = timezone.now()
            
            # Only login and dashboard access - no real duties
            activities = [
                (login_time, 'login', 'Teacher logged in to system'),
                (login_time.replace(minute=login_time.minute + 5), 'dashboard_access', 'Accessed teacher dashboard'),
                (login_time.replace(minute=login_time.minute + 10), 'system_navigation', 'Browsed around system'),
                (login_time.replace(minute=login_time.minute + 15), 'logout', 'Teacher logged out'),
            ]
            
            # Create activity logs
            for activity_time, activity_type, description in activities:
                TeacherActivityLog.objects.create(
                    teacher=teacher,
                    activity_type=activity_type,
                    description=description,
                    timestamp=activity_time,
                    ip_address='127.0.0.1'
                )
            
            # Create attendance record
            attendance = TeacherAttendance.objects.create(
                teacher=teacher,
                date=today,
                first_activity_time=activities[0][0],
                last_activity_time=activities[-1][0],
                check_in_time=activities[0][0].time(),
                check_out_time=activities[-1][0].time(),
                is_auto_marked=True
            )
            
            # Calculate hours and determine status
            attendance.calculate_hours()
            attendance.determine_status_advanced()
            attendance.save()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Inactive teacher test results:'))
            self.stdout.write(f'  - Teacher: {teacher.user.get_full_name()}')
            self.stdout.write(f'  - Date: {attendance.date}')
            self.stdout.write(f'  - Status: {attendance.get_status_display()} (Should be Absent)')
            self.stdout.write(f'  - First Activity: {attendance.first_activity_time.strftime("%H:%M:%S")}')
            self.stdout.write(f'  - Last Activity: {attendance.last_activity_time.strftime("%H:%M:%S")}')
            self.stdout.write(f'  - Total Hours: {attendance.total_hours}')
            self.stdout.write(f'  - Has Real Activities: {attendance.has_performed_duties()} (Should be False)')
            
            # Show activities
            all_activities = TeacherActivityLog.objects.filter(
                teacher=teacher,
                timestamp__date=today
            ).order_by('timestamp')
            
            self.stdout.write(f'\n✓ Activities (no real duties):')
            for activity in all_activities:
                self.stdout.write(f'  - {activity.timestamp.strftime("%H:%M:%S")}: {activity.get_activity_type_display()} - {activity.description}')
            
            if attendance.status == 'absent':
                self.stdout.write(self.style.SUCCESS('\n✓ CORRECT: Teacher marked as ABSENT despite logging in (no real duties performed)'))
            else:
                self.stdout.write(self.style.ERROR(f'\n✗ ERROR: Teacher should be ABSENT but marked as {attendance.get_status_display()}'))
            
            self.stdout.write('\nThis demonstrates that the system correctly identifies teachers who log in but don\'t perform actual duties.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during test: {str(e)}'))
