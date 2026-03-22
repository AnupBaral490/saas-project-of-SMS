from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog
from datetime import datetime, time, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Demonstrate enhanced real-time teacher activity tracking with detailed timestamps'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== ENHANCED REAL-TIME TEACHER TRACKING DEMO ==='))
        
        # Get all teachers
        teachers = TeacherProfile.objects.select_related('user')[:3]  # Limit to 3 for demo
        
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('No teachers found. Please create teachers first.'))
            return
        
        today = timezone.now().date()
        
        # Clear existing data for clean demo
        TeacherActivityLog.objects.filter(timestamp__date=today).delete()
        TeacherAttendance.objects.filter(date=today).delete()
        
        self.stdout.write('Creating realistic teacher activity scenarios...\n')
        
        # Scenario 1: Highly Active Teacher
        teacher1 = teachers[0]
        self.create_active_teacher_scenario(teacher1, today)
        
        # Scenario 2: Moderately Active Teacher  
        if teachers.count() > 1:
            teacher2 = teachers[1]
            self.create_moderate_teacher_scenario(teacher2, today)
        
        # Scenario 3: Inactive Teacher (just browsing)
        if teachers.count() > 2:
            teacher3 = teachers[2]
            self.create_inactive_teacher_scenario(teacher3, today)
        
        # Generate summary report
        self.generate_summary_report(today)
        
        self.stdout.write(self.style.SUCCESS('\n=== DEMO COMPLETED ==='))
        self.stdout.write('Visit these URLs to see the enhanced tracking:')
        self.stdout.write(f'📊 Dashboard: http://127.0.0.1:8075/attendance/teacher-dashboard/')
        self.stdout.write(f'📋 Detailed Activities: http://127.0.0.1:8075/attendance/teacher-activities/')
        self.stdout.write(f'⏰ Activity Timeline: http://127.0.0.1:8075/attendance/teacher-timeline/')
    
    def create_active_teacher_scenario(self, teacher, today):
        """Create scenario for a highly active teacher"""
        self.stdout.write(f'📚 Creating ACTIVE teacher scenario for: {teacher.user.get_full_name()}')
        
        base_time = timezone.now().replace(hour=8, minute=30, second=0, microsecond=0)
        
        activities = [
            # Early morning activities
            (base_time, 'first_login', 'FIRST ACTIVITY: Teacher logged in early'),
            (base_time + timedelta(minutes=10), 'dashboard_access', 'Reviewed daily schedule'),
            
            # First period - Mathematics
            (base_time + timedelta(minutes=30), 'mark_attendance', 'Marked attendance for Mathematics - Class 10A (Period 1)'),
            (base_time + timedelta(minutes=45), 'create_assignment', 'Created algebra homework assignment'),
            
            # Second period - Physics  
            (base_time + timedelta(hours=1, minutes=15), 'mark_attendance', 'Marked attendance for Physics - Class 10B (Period 2)'),
            (base_time + timedelta(hours=1, minutes=30), 'grade_exam', 'Graded physics quiz papers'),
            
            # Break time activities
            (base_time + timedelta(hours=2), 'send_message', 'Sent progress update to parent of struggling student'),
            (base_time + timedelta(hours=2, minutes=15), 'view_report', 'Reviewed class performance analytics'),
            
            # Third period - Chemistry
            (base_time + timedelta(hours=2, minutes=45), 'mark_attendance', 'Marked attendance for Chemistry - Class 11A (Period 3)'),
            (base_time + timedelta(hours=3), 'create_assignment', 'Created chemistry lab report assignment'),
            
            # Lunch break
            (base_time + timedelta(hours=4), 'grade_exam', 'Graded chemistry test papers during lunch'),
            
            # Afternoon activities
            (base_time + timedelta(hours=4, minutes=30), 'mark_attendance', 'Marked attendance for Mathematics - Class 11B (Period 4)'),
            (base_time + timedelta(hours=5), 'send_message', 'Replied to parent inquiry about homework'),
            (base_time + timedelta(hours=5, minutes=30), 'create_assignment', 'Prepared next week\'s lesson plan'),
            
            # End of day
            (base_time + timedelta(hours=6), 'view_report', 'Generated daily attendance summary'),
            (base_time + timedelta(hours=6, minutes=15), 'system_navigation', 'Final system check'),
        ]
        
        self.create_activities_and_attendance(teacher, today, activities)
        self.stdout.write(f'  ✓ Created {len(activities)} activities (4 attendance sessions, 3 assignments, 2 grading, 2 messages)')
    
    def create_moderate_teacher_scenario(self, teacher, today):
        """Create scenario for a moderately active teacher"""
        self.stdout.write(f'📖 Creating MODERATE teacher scenario for: {teacher.user.get_full_name()}')
        
        base_time = timezone.now().replace(hour=9, minute=15, second=0, microsecond=0)  # Late start
        
        activities = [
            # Late morning start
            (base_time, 'login', 'Teacher logged in (late)'),
            (base_time + timedelta(minutes=5), 'dashboard_access', 'Checked daily schedule'),
            
            # First class
            (base_time + timedelta(minutes=20), 'mark_attendance', 'Marked attendance for English - Class 9A'),
            (base_time + timedelta(minutes=45), 'create_assignment', 'Created essay writing assignment'),
            
            # Second class
            (base_time + timedelta(hours=1, minutes=30), 'mark_attendance', 'Marked attendance for English - Class 9B'),
            
            # Some administrative work
            (base_time + timedelta(hours=2, minutes=30), 'view_report', 'Reviewed student progress reports'),
            (base_time + timedelta(hours=3), 'send_message', 'Sent message to parent about student behavior'),
            
            # End of day
            (base_time + timedelta(hours=4), 'system_navigation', 'Browsed system before leaving'),
        ]
        
        self.create_activities_and_attendance(teacher, today, activities)
        self.stdout.write(f'  ✓ Created {len(activities)} activities (2 attendance sessions, 1 assignment, 1 message)')
    
    def create_inactive_teacher_scenario(self, teacher, today):
        """Create scenario for an inactive teacher (just browsing)"""
        self.stdout.write(f'💤 Creating INACTIVE teacher scenario for: {teacher.user.get_full_name()}')
        
        base_time = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        activities = [
            # Just browsing, no real work
            (base_time, 'login', 'Teacher logged in'),
            (base_time + timedelta(minutes=5), 'dashboard_access', 'Accessed dashboard'),
            (base_time + timedelta(minutes=15), 'system_navigation', 'Browsed around system'),
            (base_time + timedelta(minutes=25), 'view_report', 'Looked at reports (no action taken)'),
            (base_time + timedelta(minutes=30), 'system_navigation', 'More browsing'),
            (base_time + timedelta(minutes=35), 'logout', 'Logged out without doing work'),
        ]
        
        self.create_activities_and_attendance(teacher, today, activities)
        self.stdout.write(f'  ✓ Created {len(activities)} activities (0 attendance sessions, 0 assignments - should be marked ABSENT)')
    
    def create_activities_and_attendance(self, teacher, today, activities):
        """Create activity logs and attendance record"""
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
        
        # Calculate hours and determine status
        attendance.calculate_hours()
        attendance.determine_status_advanced()
        attendance.save()
    
    def generate_summary_report(self, today):
        """Generate summary of all teacher activities"""
        self.stdout.write('\n📊 ACTIVITY SUMMARY REPORT:')
        
        attendances = TeacherAttendance.objects.filter(date=today).select_related('teacher__user')
        
        for attendance in attendances:
            teacher_name = attendance.teacher.user.get_full_name()
            
            # Get activity counts
            activities = TeacherActivityLog.objects.filter(
                teacher=attendance.teacher,
                timestamp__date=today
            )
            
            attendance_count = activities.filter(activity_type='mark_attendance').count()
            assignment_count = activities.filter(activity_type='create_assignment').count()
            grading_count = activities.filter(activity_type='grade_exam').count()
            message_count = activities.filter(activity_type='send_message').count()
            
            # Status display
            if attendance.status == 'present':
                status_icon = '✅'
            elif attendance.status == 'late':
                status_icon = '⚠️'
            elif attendance.status == 'absent':
                status_icon = '❌'
            else:
                status_icon = '❓'
            
            self.stdout.write(f'\n{status_icon} {teacher_name} - {attendance.get_status_display()}')
            self.stdout.write(f'   🕐 Hours: {attendance.total_hours}')
            self.stdout.write(f'   📚 Attendance Sessions: {attendance_count}')
            self.stdout.write(f'   📝 Assignments: {assignment_count}')
            self.stdout.write(f'   ⭐ Grading: {grading_count}')
            self.stdout.write(f'   💬 Messages: {message_count}')
            self.stdout.write(f'   🎯 Real Duties: {"Yes" if attendance.has_performed_duties() else "No"}')
            
            if attendance.first_activity_time:
                self.stdout.write(f'   ⏰ First Activity: {attendance.first_activity_time.strftime("%H:%M:%S")}')
            if attendance.last_activity_time:
                self.stdout.write(f'   ⏰ Last Activity: {attendance.last_activity_time.strftime("%H:%M:%S")}')
