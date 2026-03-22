from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog
from datetime import datetime, time

User = get_user_model()

class Command(BaseCommand):
    help = 'Show summary of all teacher attendance with real-time tracking details'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('=== REAL-TIME TEACHER ATTENDANCE SUMMARY ==='))
        self.stdout.write(f'Date: {today}')
        self.stdout.write('')
        
        # Get all teachers with attendance records for today
        teachers_with_attendance = TeacherAttendance.objects.filter(
            date=today
        ).select_related('teacher__user').order_by('teacher__user__first_name')
        
        if not teachers_with_attendance.exists():
            self.stdout.write(self.style.WARNING('No teacher attendance records found for today.'))
            self.stdout.write('Run the following commands to generate test data:')
            self.stdout.write('  python manage.py simulate_teacher_day')
            self.stdout.write('  python manage.py test_inactive_teacher')
            return
        
        # Summary statistics
        total_teachers = teachers_with_attendance.count()
        present_teachers = teachers_with_attendance.filter(status__in=['present', 'late']).count()
        absent_teachers = teachers_with_attendance.filter(status='absent').count()
        late_teachers = teachers_with_attendance.filter(status='late').count()
        
        self.stdout.write(f'📊 SUMMARY STATISTICS:')
        self.stdout.write(f'  Total Teachers: {total_teachers}')
        self.stdout.write(f'  Present: {present_teachers}')
        self.stdout.write(f'  Absent: {absent_teachers}')
        self.stdout.write(f'  Late: {late_teachers}')
        self.stdout.write(f'  Attendance Rate: {(present_teachers/total_teachers*100):.1f}%')
        self.stdout.write('')
        
        # Detailed breakdown
        self.stdout.write('📋 DETAILED BREAKDOWN:')
        self.stdout.write('')
        
        for attendance in teachers_with_attendance:
            teacher_name = attendance.teacher.user.get_full_name()
            
            # Get activity count
            activity_count = TeacherActivityLog.objects.filter(
                teacher=attendance.teacher,
                timestamp__date=today
            ).count()
            
            # Get significant activities count
            significant_activities = TeacherActivityLog.objects.filter(
                teacher=attendance.teacher,
                timestamp__date=today,
                activity_type__in=['mark_attendance', 'create_assignment', 'grade_exam']
            ).count()
            
            # Status color
            if attendance.status == 'present':
                status_display = self.style.SUCCESS(f'✓ {attendance.get_status_display()}')
            elif attendance.status == 'late':
                status_display = self.style.WARNING(f'⚠ {attendance.get_status_display()}')
            elif attendance.status == 'absent':
                status_display = self.style.ERROR(f'✗ {attendance.get_status_display()}')
            else:
                status_display = f'• {attendance.get_status_display()}'
            
            self.stdout.write(f'👤 {teacher_name}')
            self.stdout.write(f'   Status: {status_display}')
            
            if attendance.first_activity_time:
                self.stdout.write(f'   First Activity: {attendance.first_activity_time.strftime("%H:%M:%S")} (Real-time)')
            elif attendance.check_in_time:
                self.stdout.write(f'   Check In: {attendance.check_in_time} (Manual)')
            else:
                self.stdout.write(f'   Check In: Not recorded')
            
            if attendance.last_activity_time:
                self.stdout.write(f'   Last Activity: {attendance.last_activity_time.strftime("%H:%M:%S")} (Real-time)')
            elif attendance.check_out_time:
                self.stdout.write(f'   Check Out: {attendance.check_out_time} (Manual)')
            else:
                self.stdout.write(f'   Check Out: Not recorded')
            
            self.stdout.write(f'   Total Hours: {attendance.total_hours}')
            self.stdout.write(f'   Total Activities: {activity_count}')
            self.stdout.write(f'   Significant Duties: {significant_activities}')
            self.stdout.write(f'   Has Real Duties: {"Yes" if attendance.has_performed_duties() else "No"}')
            self.stdout.write('')
        
        # Recent activities
        self.stdout.write('🕒 RECENT ACTIVITIES (Last 10):')
        recent_activities = TeacherActivityLog.objects.filter(
            timestamp__date=today
        ).select_related('teacher__user').order_by('-timestamp')[:10]
        
        for activity in recent_activities:
            teacher_name = activity.teacher.user.get_full_name()
            time_str = activity.timestamp.strftime("%H:%M:%S")
            self.stdout.write(f'  {time_str} - {teacher_name}: {activity.get_activity_type_display()}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== KEY FEATURES DEMONSTRATED ==='))
        self.stdout.write('✓ Real-time activity tracking (not just login/logout)')
        self.stdout.write('✓ Activity-based attendance validation')
        self.stdout.write('✓ Automatic status determination')
        self.stdout.write('✓ Fraud prevention (login without work = absent)')
        self.stdout.write('✓ Detailed activity audit trail')
        self.stdout.write('')
        self.stdout.write(f'🌐 View dashboard: http://127.0.0.1:8075/attendance/teacher-dashboard/')