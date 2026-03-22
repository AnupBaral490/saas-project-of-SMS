from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog, TeacherSchedule, GeofenceLocation

User = get_user_model()

class Command(BaseCommand):
    help = 'Show all enhanced automatic teacher attendance features'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('🎯 ENHANCED AUTOMATIC TEACHER ATTENDANCE SYSTEM'))
        self.stdout.write('=' * 70)
        
        # System Overview
        self.stdout.write('\n📊 SYSTEM OVERVIEW:')
        
        total_teachers = TeacherProfile.objects.count()
        teachers_with_schedules = TeacherProfile.objects.filter(schedules__isnull=False).distinct().count()
        today_activities = TeacherActivityLog.objects.filter(timestamp__date=today).count()
        today_attendance = TeacherAttendance.objects.filter(date=today).count()
        geofence_locations = GeofenceLocation.objects.filter(is_active=True).count()
        
        self.stdout.write(f'  👥 Total Teachers: {total_teachers}')
        self.stdout.write(f'  📅 Teachers with Schedules: {teachers_with_schedules}')
        self.stdout.write(f'  📍 Active Geofence Locations: {geofence_locations}')
        self.stdout.write(f'  🕒 Today\'s Activities: {today_activities}')
        self.stdout.write(f'  ✅ Today\'s Attendance Records: {today_attendance}')
        
        # Key Enhancements
        self.stdout.write('\n🚀 KEY ENHANCEMENTS OVER PREVIOUS SYSTEM:')
        
        enhancements = [
            ('Schedule-Based Validation', 'Attendance validated against actual class schedules'),
            ('Performance Scoring', 'Comprehensive 0-100 scoring based on multiple factors'),
            ('Class Compliance Tracking', 'Monitors attendance to scheduled classes'),
            ('Location Verification', 'IP-based and geofence location validation'),
            ('Activity Prioritization', 'High/Medium/Low priority classification'),
            ('Punctuality Analysis', 'Tracks on-time vs late class attendance'),
            ('Comprehensive Reporting', 'Detailed compliance and performance reports'),
            ('Zero Manual Input', 'Completely automatic with no manual attendance required'),
        ]
        
        for enhancement, description in enhancements:
            self.stdout.write(f'  ✅ {enhancement}: {description}')
        
        # Validation Methods
        self.stdout.write('\n🎯 AUTOMATIC VALIDATION METHODS:')
        
        validation_methods = [
            ('Schedule-Based', 'Primary method using teacher class schedules'),
            ('Activity-Based', 'Validates based on educational activities performed'),
            ('Geolocation', 'Verifies teacher presence on campus'),
            ('Biometric', 'Ready for fingerprint/face recognition integration'),
        ]
        
        for method, description in validation_methods:
            self.stdout.write(f'  🔍 {method}: {description}')
        
        # Performance Scoring Components
        self.stdout.write('\n📊 PERFORMANCE SCORING (0-100 POINTS):')
        
        scoring_components = [
            ('Schedule Compliance', '40 points', 'Percentage of scheduled classes attended'),
            ('Punctuality', '20 points', 'On-time arrival to scheduled classes'),
            ('Activity Performance', '40 points', 'Educational duties and activities performed'),
        ]
        
        for component, points, description in scoring_components:
            self.stdout.write(f'  📈 {component} ({points}): {description}')
        
        # Status Determination Logic
        self.stdout.write('\n🎯 ENHANCED STATUS DETERMINATION:')
        
        status_logic = [
            ('Present', '100% class attendance + on-time arrival + duties performed'),
            ('Late', '100% class attendance + late arrival + duties performed'),
            ('Partial', '50-99% class attendance + some duties performed'),
            ('Half Day', '<4 hours worked but educational duties performed'),
            ('Absent', 'No scheduled classes attended or no educational duties'),
        ]
        
        for status, criteria in status_logic:
            self.stdout.write(f'  📋 {status}: {criteria}')
        
        # Activity Categories
        self.stdout.write('\n📝 ENHANCED ACTIVITY TRACKING:')
        
        activity_categories = {
            'High Priority (Educational)': [
                'mark_attendance - Marking student attendance for assigned classes',
                'create_assignment - Creating assignments and lesson materials',
                'grade_exam - Grading exams and assessments',
                'classroom_entry - Physical classroom presence detection'
            ],
            'Medium Priority (Administrative)': [
                'send_message - Communication with parents/students',
                'view_report - Accessing reports and analytics',
                'biometric_scan - Biometric verification activities'
            ],
            'Low Priority (System)': [
                'login/logout - Basic authentication activities',
                'dashboard_access - General dashboard usage',
                'system_navigation - General system browsing'
            ]
        }
        
        for category, activities in activity_categories.items():
            self.stdout.write(f'\n  📂 {category}:')
            for activity in activities:
                self.stdout.write(f'     • {activity}')
        
        # Location Tracking
        self.stdout.write('\n📍 LOCATION VERIFICATION:')
        
        if geofence_locations > 0:
            locations = GeofenceLocation.objects.filter(is_active=True)
            for location in locations:
                self.stdout.write(f'  🏫 {location.name}: {location.radius_meters}m radius')
                self.stdout.write(f'     Coordinates: {location.center_lat}, {location.center_lng}')
        else:
            self.stdout.write('  📍 No geofence locations configured')
        
        # Management Commands
        self.stdout.write('\n🛠️ MANAGEMENT COMMANDS:')
        
        commands = [
            ('setup_teacher_schedules', 'Set up weekly schedules for all teachers'),
            ('demo_schedule_based_attendance', 'Demonstrate enhanced attendance system'),
            ('test_enhanced_attendance', 'Test schedule validation with real scenarios'),
            ('show_enhanced_features', 'Show this comprehensive feature overview'),
        ]
        
        for command, description in commands:
            self.stdout.write(f'  python manage.py {command}')
            self.stdout.write(f'    └─ {description}')
        
        # Dashboard URLs
        self.stdout.write('\n🌐 ENHANCED DASHBOARD VIEWS:')
        
        dashboard_urls = [
            ('Main Dashboard', '/attendance/teacher-dashboard/', 'Real-time attendance with performance scores'),
            ('Detailed Activities', '/attendance/teacher-activities/', 'Teacher-specific activity breakdown'),
            ('Activity Timeline', '/attendance/teacher-timeline/', 'Chronological activity view'),
            ('Comprehensive Reports', '/attendance/teacher-reports/', 'Detailed reports with CSV export'),
        ]
        
        for name, url, description in dashboard_urls:
            self.stdout.write(f'  📊 {name}:')
            self.stdout.write(f'     URL: http://127.0.0.1:8075{url}')
            self.stdout.write(f'     Features: {description}')
        
        # Recent Performance Summary
        if today_attendance > 0:
            attendances = TeacherAttendance.objects.filter(date=today)
            avg_performance = sum(att.get_performance_score() for att in attendances) / attendances.count()
            present_count = attendances.filter(status__in=['present', 'late']).count()
            
            self.stdout.write(f'\n📈 TODAY\'S PERFORMANCE SUMMARY:')
            self.stdout.write(f'  📊 Average Performance Score: {avg_performance:.1f}/100')
            self.stdout.write(f'  ✅ Present/Late Teachers: {present_count}/{attendances.count()}')
            self.stdout.write(f'  🎯 Attendance Rate: {(present_count/attendances.count()*100):.1f}%')
            
            # Show top performer
            top_performer = attendances.order_by('-attendance_percentage', '-total_hours').first()
            if top_performer:
                self.stdout.write(f'  🏆 Top Performer: {top_performer.teacher.user.get_full_name()} ({top_performer.get_performance_score()}/100)')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('🎉 ENHANCED AUTOMATIC ATTENDANCE SYSTEM READY!'))
        self.stdout.write('\nNo Manual Attendance Required - Everything is Automatic!')
        self.stdout.write('✅ Schedule-based validation')
        self.stdout.write('✅ Real-time activity tracking')
        self.stdout.write('✅ Performance scoring')
        self.stdout.write('✅ Location verification')
        self.stdout.write('✅ Comprehensive reporting')
        
        self.stdout.write('\n👉 Start by visiting: http://127.0.0.1:8075/attendance/teacher-dashboard/')