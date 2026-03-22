from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog, TeacherSchedule, AttendanceSession
from academic.models import TeacherSubjectAssignment
from datetime import datetime, time, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Test enhanced automatic teacher attendance system with schedule validation'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎯 TESTING ENHANCED AUTOMATIC TEACHER ATTENDANCE SYSTEM'))
        self.stdout.write('=' * 70)
        
        today = timezone.now().date()
        
        # Clear existing data for clean test
        TeacherActivityLog.objects.filter(timestamp__date=today).delete()
        TeacherAttendance.objects.filter(date=today).delete()
        AttendanceSession.objects.filter(date=today).delete()
        
        # Get teachers with schedules
        teachers_with_schedules = TeacherProfile.objects.filter(
            schedules__is_active=True
        ).distinct()
        
        if not teachers_with_schedules.exists():
            self.stdout.write(self.style.ERROR('No teachers with schedules found. Run setup_teacher_schedules first.'))
            return
        
        # Test different scenarios
        for i, teacher in enumerate(teachers_with_schedules[:3]):  # Test up to 3 teachers
            if i == 0:
                self.test_perfect_teacher(teacher, today)
            elif i == 1:
                self.test_late_teacher(teacher, today)
            else:
                self.test_absent_teacher(teacher, today)
        
        # Generate comprehensive report
        self.generate_enhanced_report(today)
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('🎉 ENHANCED ATTENDANCE SYSTEM TEST COMPLETED!'))
        self.stdout.write('\nKey Features Demonstrated:')
        self.stdout.write('✅ Schedule-based validation')
        self.stdout.write('✅ Automatic status determination')
        self.stdout.write('✅ Performance scoring')
        self.stdout.write('✅ Class compliance tracking')
        self.stdout.write('✅ Location verification')
        self.stdout.write('\n📊 View results: http://127.0.0.1:8075/attendance/teacher-dashboard/')
    
    def test_perfect_teacher(self, teacher, today):
        """Test scenario: Teacher follows schedule perfectly"""
        self.stdout.write(f'\n🌟 TESTING PERFECT TEACHER: {teacher.user.get_full_name()}')
        
        # Get teacher's schedule for today
        weekday = today.weekday()
        schedules = TeacherSchedule.objects.filter(
            teacher=teacher,
            day_of_week=weekday,
            is_active=True
        ).order_by('start_time')
        
        if not schedules.exists():
            self.stdout.write('  No classes scheduled for today')
            return
        
        # Create activities following the schedule perfectly
        activities = []
        
        # Early login before first class
        first_class = schedules.first()
        login_time = timezone.now().replace(
            hour=first_class.start_time.hour - 1,
            minute=30,
            second=0,
            microsecond=0
        )
        
        activities.append((login_time, 'first_login', 'FIRST ACTIVITY: Early login before classes'))
        
        # Attend each scheduled class
        for schedule in schedules:
            class_start = timezone.now().replace(
                hour=schedule.start_time.hour,
                minute=schedule.start_time.minute,
                second=0,
                microsecond=0
            )
            
            # Mark attendance for the class
            activities.append((
                class_start + timedelta(minutes=5),
                'mark_attendance',
                f'Marked attendance for {schedule.subject_assignment.subject.name} - {schedule.subject_assignment.class_assigned}'
            ))
            
            # Create attendance session
            AttendanceSession.objects.create(
                teacher_assignment=schedule.subject_assignment,
                date=today,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                topic_covered=f'Chapter on {schedule.subject_assignment.subject.name}',
                is_completed=True
            )
            
            # Additional activities during class
            activities.append((
                class_start + timedelta(minutes=20),
                'create_assignment',
                f'Created assignment for {schedule.subject_assignment.subject.name}'
            ))
        
        # End of day activities
        last_class = schedules.last()
        end_time = timezone.now().replace(
            hour=last_class.end_time.hour,
            minute=last_class.end_time.minute + 30,
            second=0,
            microsecond=0
        )
        
        activities.append((end_time, 'view_report', 'Reviewed daily reports'))
        activities.append((end_time + timedelta(minutes=15), 'logout', 'Logged out after completing all duties'))
        
        # Create all activities and attendance record
        self.create_activities_and_attendance(teacher, today, activities, 'schedule_based')
        
        self.stdout.write(f'  ✅ Created {len(activities)} activities')
        self.stdout.write(f'  ✅ Attended all {schedules.count()} scheduled classes')
        self.stdout.write('  ✅ Expected Status: Present with 100% compliance')
    
    def test_late_teacher(self, teacher, today):
        """Test scenario: Teacher arrives late but attends most classes"""
        self.stdout.write(f'\n⚠️ TESTING LATE TEACHER: {teacher.user.get_full_name()}')
        
        # Get teacher's schedule for today
        weekday = today.weekday()
        schedules = TeacherSchedule.objects.filter(
            teacher=teacher,
            day_of_week=weekday,
            is_active=True
        ).order_by('start_time')
        
        if not schedules.exists():
            self.stdout.write('  No classes scheduled for today')
            return
        
        activities = []
        
        # Late login - arrives 45 minutes after first class
        first_class = schedules.first()
        late_login_time = timezone.now().replace(
            hour=first_class.start_time.hour,
            minute=first_class.start_time.minute + 45,
            second=0,
            microsecond=0
        )
        
        activities.append((late_login_time, 'login', 'Late login - missed first class'))
        
        # Miss first class, attend the rest
        attended_classes = 0
        for i, schedule in enumerate(schedules):
            if i == 0:
                # Miss first class
                continue
            
            class_start = timezone.now().replace(
                hour=schedule.start_time.hour,
                minute=schedule.start_time.minute,
                second=0,
                microsecond=0
            )
            
            # Attend class (but slightly late)
            activities.append((
                class_start + timedelta(minutes=10),
                'mark_attendance',
                f'Marked attendance for {schedule.subject_assignment.subject.name} (10 min late)'
            ))
            
            # Create attendance session
            AttendanceSession.objects.create(
                teacher_assignment=schedule.subject_assignment,
                date=today,
                start_time=time(schedule.start_time.hour, schedule.start_time.minute + 10),
                end_time=schedule.end_time,
                topic_covered=f'Partial chapter on {schedule.subject_assignment.subject.name}',
                is_completed=True
            )
            
            attended_classes += 1
        
        # Some end-of-day activities
        activities.append((
            timezone.now().replace(hour=15, minute=0, second=0, microsecond=0),
            'send_message',
            'Sent apology message to admin for being late'
        ))
        
        # Create activities and attendance record
        self.create_activities_and_attendance(teacher, today, activities, 'schedule_based')
        
        self.stdout.write(f'  ⚠️ Created {len(activities)} activities')
        self.stdout.write(f'  ⚠️ Attended {attended_classes}/{schedules.count()} scheduled classes')
        self.stdout.write('  ⚠️ Expected Status: Late with partial compliance')
    
    def test_absent_teacher(self, teacher, today):
        """Test scenario: Teacher logs in but doesn't attend any classes"""
        self.stdout.write(f'\n❌ TESTING ABSENT TEACHER: {teacher.user.get_full_name()}')
        
        activities = [
            (timezone.now().replace(hour=10, minute=30, second=0, microsecond=0), 'login', 'Logged in but no classes'),
            (timezone.now().replace(hour=10, minute=35, second=0, microsecond=0), 'dashboard_access', 'Browsed dashboard'),
            (timezone.now().replace(hour=10, minute=45, second=0, microsecond=0), 'system_navigation', 'General browsing'),
            (timezone.now().replace(hour=11, minute=0, second=0, microsecond=0), 'logout', 'Logged out without attending classes'),
        ]
        
        # Create activities and attendance record (no attendance sessions created)
        self.create_activities_and_attendance(teacher, today, activities, 'activity_based')
        
        self.stdout.write(f'  ❌ Created {len(activities)} activities')
        self.stdout.write('  ❌ Attended 0 scheduled classes')
        self.stdout.write('  ❌ Expected Status: Absent (no real duties performed)')
    
    def create_activities_and_attendance(self, teacher, today, activities, validation_method):
        """Create activity logs and attendance record with enhanced tracking"""
        # Create activity logs
        for activity_time, activity_type, description in activities:
            # Determine priority based on activity type
            if activity_type in ['mark_attendance', 'create_assignment', 'grade_exam']:
                priority_level = 'high'
            elif activity_type in ['send_message', 'view_report']:
                priority_level = 'medium'
            else:
                priority_level = 'low'
            
            TeacherActivityLog.objects.create(
                teacher=teacher,
                activity_type=activity_type,
                priority_level=priority_level,
                description=description,
                timestamp=activity_time,
                ip_address='127.0.0.1',
                is_on_campus=True
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
            validation_method=validation_method,
            location_verified=True,
            is_auto_marked=True
        )
        
        # Calculate all metrics using enhanced logic
        attendance.calculate_scheduled_hours()
        attendance.calculate_hours()
        attendance.determine_status_advanced()
        attendance.save()
    
    def generate_enhanced_report(self, today):
        """Generate comprehensive report of enhanced attendance system"""
        self.stdout.write('\n📊 ENHANCED ATTENDANCE SYSTEM REPORT:')
        self.stdout.write('=' * 50)
        
        attendances = TeacherAttendance.objects.filter(date=today).select_related('teacher__user')
        
        for attendance in attendances:
            teacher_name = attendance.teacher.user.get_full_name()
            
            # Get performance score
            performance_score = attendance.get_performance_score()
            
            # Get schedule compliance
            compliance_report = attendance.get_schedule_compliance_report()
            missed_classes = attendance.get_missed_classes()
            
            # Status display with emoji
            status_emoji = {
                'present': '✅',
                'late': '⚠️',
                'absent': '❌',
                'partial': '🔶',
                'half_day': '🕐'
            }.get(attendance.status, '❓')
            
            self.stdout.write(f'\n{status_emoji} {teacher_name} - {attendance.get_status_display()}')
            self.stdout.write(f'   📊 Performance Score: {performance_score}/100')
            self.stdout.write(f'   ⏰ Hours: {attendance.total_hours}/{attendance.scheduled_hours}')
            self.stdout.write(f'   📚 Classes: {attendance.classes_attended}/{attendance.classes_scheduled}')
            self.stdout.write(f'   📈 Attendance Rate: {attendance.attendance_percentage:.1f}%')
            self.stdout.write(f'   🎯 Validation: {attendance.get_validation_method_display()}')
            self.stdout.write(f'   📍 Location Verified: {"Yes" if attendance.location_verified else "No"}')
            
            if missed_classes:
                self.stdout.write(f'   ❌ Missed Classes: {len(missed_classes)}')
                for missed in missed_classes:
                    schedule = missed['schedule']
                    self.stdout.write(f'      • {schedule.start_time}-{schedule.end_time}: {schedule.subject_assignment.subject.name}')
            
            # Show activity breakdown
            activities = TeacherActivityLog.objects.filter(
                teacher=attendance.teacher,
                timestamp__date=today
            )
            
            high_priority = activities.filter(priority_level='high').count()
            medium_priority = activities.filter(priority_level='medium').count()
            low_priority = activities.filter(priority_level='low').count()
            
            self.stdout.write(f'   🎯 Activities: High({high_priority}) Medium({medium_priority}) Low({low_priority})')
        
        # System summary
        total_teachers = attendances.count()
        if total_teachers > 0:
            present_teachers = attendances.filter(status__in=['present', 'late']).count()
            avg_performance = sum(att.get_performance_score() for att in attendances) / total_teachers
            attendance_rate = (present_teachers/total_teachers*100)
        else:
            present_teachers = 0
            avg_performance = 0
            attendance_rate = 0
        
        self.stdout.write(f'\n📈 SYSTEM SUMMARY:')
        self.stdout.write(f'   👥 Total Teachers: {total_teachers}')
        self.stdout.write(f'   ✅ Present/Late: {present_teachers}')
        self.stdout.write(f'   📊 Avg Performance: {avg_performance:.1f}/100')
        self.stdout.write(f'   🎯 Attendance Rate: {attendance_rate:.1f}%')