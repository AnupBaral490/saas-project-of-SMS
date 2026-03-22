from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Show all available real-time teacher tracking features and URLs'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('🎯 ENHANCED REAL-TIME TEACHER TRACKING SYSTEM'))
        self.stdout.write('=' * 60)
        
        # System Overview
        self.stdout.write('\n📊 SYSTEM OVERVIEW:')
        
        # Get statistics
        total_teachers = TeacherProfile.objects.count()
        today_activities = TeacherActivityLog.objects.filter(timestamp__date=today).count()
        today_attendance = TeacherAttendance.objects.filter(date=today).count()
        
        self.stdout.write(f'  👥 Total Teachers: {total_teachers}')
        self.stdout.write(f'  📅 Today\'s Activities: {today_activities}')
        self.stdout.write(f'  ✅ Attendance Records: {today_attendance}')
        
        # Available Views
        self.stdout.write('\n🌐 AVAILABLE DASHBOARD VIEWS:')
        self.stdout.write('  📊 Main Dashboard:')
        self.stdout.write('     URL: http://127.0.0.1:8075/attendance/teacher-dashboard/')
        self.stdout.write('     Features: Real-time attendance, activity validation, summary stats')
        
        self.stdout.write('\n  📋 Detailed Activities:')
        self.stdout.write('     URL: http://127.0.0.1:8075/attendance/teacher-activities/')
        self.stdout.write('     Features: Teacher-specific activity breakdown, productivity metrics')
        
        self.stdout.write('\n  ⏰ Activity Timeline:')
        self.stdout.write('     URL: http://127.0.0.1:8075/attendance/teacher-timeline/')
        self.stdout.write('     Features: Chronological activity view, filtering, real-time updates')
        
        self.stdout.write('\n  📈 Detailed Reports:')
        self.stdout.write('     URL: http://127.0.0.1:8075/attendance/teacher-reports/')
        self.stdout.write('     Features: Comprehensive reports, CSV export, filtering')
        
        # Key Features
        self.stdout.write('\n🚀 KEY FEATURES:')
        
        features = [
            ('Real-Time Tracking', 'Activities captured automatically as they happen'),
            ('Activity Validation', 'Attendance based on actual educational duties performed'),
            ('Fraud Prevention', 'Cannot fake attendance with empty logins'),
            ('Detailed Timestamps', 'Exact time recording for all activities'),
            ('Productivity Analytics', 'Performance metrics and improvement suggestions'),
            ('Live Monitoring', 'Auto-refreshing dashboards with current status'),
            ('Category Breakdown', 'Activities grouped by type and importance'),
            ('IP Tracking', 'Location verification for security'),
        ]
        
        for feature, description in features:
            self.stdout.write(f'  ✅ {feature}: {description}')
        
        # Activity Types
        self.stdout.write('\n📝 TRACKED ACTIVITY TYPES:')
        
        activity_categories = {
            'Educational Activities (High Priority)': [
                'mark_attendance - Marking student attendance',
                'create_assignment - Creating/updating assignments', 
                'grade_exam - Grading exams and assessments',
                'send_message - Communication with parents/students'
            ],
            'Administrative Activities (Medium Priority)': [
                'view_report - Accessing reports and analytics',
                'dashboard_access - Reviewing schedules and notifications'
            ],
            'System Activities (Low Priority)': [
                'login/logout - Authentication activities',
                'system_navigation - General browsing'
            ]
        }
        
        for category, activities in activity_categories.items():
            self.stdout.write(f'\n  📂 {category}:')
            for activity in activities:
                self.stdout.write(f'     • {activity}')
        
        # Status Logic
        self.stdout.write('\n🎯 ATTENDANCE STATUS LOGIC:')
        status_rules = [
            ('Present', 'First activity before 9:00 AM + Real educational duties'),
            ('Late', 'First activity 9:00-9:30 AM + Real educational duties'),
            ('Absent', 'No real educational duties (regardless of login)'),
            ('Half Day', 'Less than 4 hours but educational duties performed')
        ]
        
        for status, rule in status_rules:
            self.stdout.write(f'  {status}: {rule}')
        
        # Management Commands
        self.stdout.write('\n🛠️ MANAGEMENT COMMANDS:')
        commands = [
            ('demo_enhanced_tracking', 'Generate comprehensive demo data'),
            ('simulate_teacher_day', 'Simulate full day activities'),
            ('test_inactive_teacher', 'Test fraud prevention'),
            ('show_attendance_summary', 'Display current status'),
            ('show_tracking_features', 'Show this help (current command)')
        ]
        
        for command, description in commands:
            self.stdout.write(f'  python manage.py {command}')
            self.stdout.write(f'    └─ {description}')
        
        # Recent Activity Sample
        recent_activities = TeacherActivityLog.objects.select_related('teacher__user').order_by('-timestamp')[:5]
        
        if recent_activities.exists():
            self.stdout.write('\n🕒 RECENT ACTIVITIES (Last 5):')
            for activity in recent_activities:
                teacher_name = activity.teacher.user.get_full_name()
                time_str = activity.timestamp.strftime('%H:%M:%S')
                self.stdout.write(f'  {time_str} - {teacher_name}: {activity.get_activity_type_display()}')
        
        # Performance Summary
        if today_attendance > 0:
            present_count = TeacherAttendance.objects.filter(
                date=today, 
                status__in=['present', 'late']
            ).count()
            
            attendance_rate = (present_count / today_attendance * 100) if today_attendance > 0 else 0
            
            self.stdout.write(f'\n📈 TODAY\'S PERFORMANCE:')
            self.stdout.write(f'  Attendance Rate: {attendance_rate:.1f}%')
            self.stdout.write(f'  Total Activities: {today_activities}')
            self.stdout.write(f'  Active Teachers: {present_count}/{today_attendance}')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 SYSTEM READY FOR REAL-TIME TEACHER TRACKING!'))
        self.stdout.write('\nStart by visiting the main dashboard:')
        self.stdout.write('👉 http://127.0.0.1:8075/attendance/teacher-dashboard/')