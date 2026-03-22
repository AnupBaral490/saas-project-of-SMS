from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from attendance.models import TeacherAttendance, TeacherActivityLog, TeacherSchedule, AttendanceSession
from academic.models import TeacherSubjectAssignment
from datetime import datetime, time, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Demonstrate enhanced schedule-based automatic teacher attendance'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎯 ENHANCED SCHEDULE-BASED ATTENDANCE DEMO'))
        self.stdout.write('=' * 60)
        
        today = timezone.now().date()
        
        # Clear existing data
        TeacherActivityLog.objects.filter(timestamp__date=today).delete()
        TeacherAttendance.objects.filter(date=today).delete()
        AttendanceSession.objects.filter(date=today).delete()
        
        # Get teachers
        teachers = TeacherProfile.objects.select_related('user')[:3]
        
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('No teachers found.'))
            return
        
        # Create demo scenarios for each teacher
        for i, teacher in enumerate(teachers):
            if i == 0:
                self.demo_excellent_teacher(teacher, today)
            elif i == 1:
                self.demo_partial_teacher(teacher, today)
            else:
                self.demo_poor_teacher(teacher, today)
        
        # Show results
        self.show_enhanced_results(today)
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 ENHANCED ATTENDANCE DEMO COMPLETED!'))
        self.stdout.write('\nKey Improvements Demonstrated:')
        self.stdout.write('✅ No manual attendance required')
        self.stdout.write('✅ Schedule-based validation')
        self.stdout.write('✅ Performance scoring (0-100)')
        self.stdout.write('✅ Activity prioritization')
        self.stdout.write('✅ Location verification')
        self.stdout.write('✅ Comprehensive compliance tracking')
    
    def demo_excellent_teacher(self, teacher, today):
        """Demo: Teacher with excellent performance"""
        self.stdout.write(f'\n🌟 EXCELLENT TEACHER: {teacher.user.get_full_name()}')
        
        # Create realistic schedule for today
        self.create_demo_schedule(teacher, today)
        
        # Create activities showing excellent performance
        base_time = timezone.now().replace(hour=8, minute=30, second=0, microsecond=0)
        
        activities = [
            # Early arrival and preparation
            (base_time, 'first_login', 'FIRST ACTIVITY: Early arrival for preparation'),
            (base_time + timedelta(minutes=15), 'dashboard_access', 'Reviewed daily schedule and notifications'),
            
            # First class period
            (base_time + timedelta(minutes=30), 'mark_attendance', 'Marked attendance for Mathematics - Class 10A'),
            (base_time + timedelta(minutes=45), 'create_assignment', 'Created homework assignment for Mathematics'),
            
            # Second class period
            (base_time + timedelta(hours=1, minutes=30), 'mark_attendance', 'Marked attendance for Physics - Class 10B'),
            (base_time + timedelta(hours=1, minutes=50), 'grade_exam', 'Graded physics quiz papers'),
            
            # Third class period
            (base_time + timedelta(hours=3), 'mark_attendance', 'Marked attendance for Chemistry - Class 11A'),
            (base_time + timedelta(hours=3, minutes=20), 'create_assignment', 'Created lab assignment for Chemistry'),
            
            # Administrative work
            (base_time + timedelta(hours=4, minutes=30), 'send_message', 'Sent progress updates to parents'),
            (base_time + timedelta(hours=5), 'view_report', 'Reviewed student performance analytics'),
            (base_time + timedelta(hours=6), 'grade_exam', 'Completed grading pending assignments'),
            
            # End of day
            (base_time + timedelta(hours=7), 'system_navigation', 'Final system check before leaving'),
        ]
        
        # Create attendance sessions for scheduled classes
        self.create_demo_sessions(teacher, today, 3)  # 3 classes attended
        
        # Create activities and attendance
        self.create_enhanced_attendance(teacher, today, activities, 3, 3)  # 3/3 classes
        
        self.stdout.write(f'  ✅ {len(activities)} activities created')
        self.stdout.write('  ✅ All scheduled classes attended')
        self.stdout.write('  ✅ Expected: Present with 100% performance score')
    
    def demo_partial_teacher(self, teacher, today):
        """Demo: Teacher with partial performance"""
        self.stdout.write(f'\n🔶 PARTIAL TEACHER: {teacher.user.get_full_name()}')
        
        # Create realistic schedule
        self.create_demo_schedule(teacher, today)
        
        # Late start, missed some classes
        base_time = timezone.now().replace(hour=10, minute=15, second=0, microsecond=0)
        
        activities = [
            # Late arrival
            (base_time, 'login', 'Late login - personal emergency'),
            (base_time + timedelta(minutes=10), 'dashboard_access', 'Checked missed notifications'),
            
            # Attended some classes
            (base_time + timedelta(minutes=30), 'mark_attendance', 'Marked attendance for Physics - Class 10B (late)'),
            (base_time + timedelta(hours=1, minutes=30), 'mark_attendance', 'Marked attendance for Chemistry - Class 11A'),
            (base_time + timedelta(hours=1, minutes=45), 'create_assignment', 'Created makeup assignment'),
            
            # Some administrative work
            (base_time + timedelta(hours=3), 'send_message', 'Sent apology message for missed class'),
            (base_time + timedelta(hours=4), 'view_report', 'Reviewed attendance reports'),
        ]
        
        # Create attendance sessions for some classes
        self.create_demo_sessions(teacher, today, 2)  # 2 out of 3 classes attended
        
        # Create activities and attendance
        self.create_enhanced_attendance(teacher, today, activities, 2, 3)  # 2/3 classes
        
        self.stdout.write(f'  🔶 {len(activities)} activities created')
        self.stdout.write('  🔶 Attended 2/3 scheduled classes')
        self.stdout.write('  🔶 Expected: Partial with ~70% performance score')
    
    def demo_poor_teacher(self, teacher, today):
        """Demo: Teacher with poor performance"""
        self.stdout.write(f'\n❌ POOR TEACHER: {teacher.user.get_full_name()}')
        
        # Create realistic schedule
        self.create_demo_schedule(teacher, today)
        
        # Minimal activity, no real work
        base_time = timezone.now().replace(hour=11, minute=0, second=0, microsecond=0)
        
        activities = [
            # Late login, minimal activity
            (base_time, 'login', 'Very late login'),
            (base_time + timedelta(minutes=10), 'dashboard_access', 'Brief dashboard check'),
            (base_time + timedelta(minutes=20), 'system_navigation', 'Browsed system without purpose'),
            (base_time + timedelta(minutes=30), 'view_report', 'Looked at reports but took no action'),
            (base_time + timedelta(minutes=45), 'logout', 'Left without attending any classes'),
        ]
        
        # No attendance sessions created (didn't attend any classes)
        
        # Create activities and attendance
        self.create_enhanced_attendance(teacher, today, activities, 0, 3)  # 0/3 classes
        
        self.stdout.write(f'  ❌ {len(activities)} activities created')
        self.stdout.write('  ❌ Attended 0/3 scheduled classes')
        self.stdout.write('  ❌ Expected: Absent with low performance score')
    
    def create_demo_schedule(self, teacher, today):
        """Create demo schedule for the teacher"""
        weekday = today.weekday()
        
        # Clear existing schedules for this teacher
        TeacherSchedule.objects.filter(teacher=teacher).delete()
        
        # Get teacher's subject assignments
        assignments = TeacherSubjectAssignment.objects.filter(teacher=teacher)[:3]
        
        if not assignments.exists():
            # Create demo assignment if none exist
            from academic.models import Subject, Class, AcademicYear
            
            try:
                subject = Subject.objects.first()
                class_obj = Class.objects.first()
                academic_year = AcademicYear.objects.first()
                
                if subject and class_obj and academic_year:
                    assignment = TeacherSubjectAssignment.objects.create(
                        teacher=teacher,
                        subject=subject,
                        class_assigned=class_obj,
                        academic_year=academic_year
                    )
                    assignments = [assignment]
            except:
                assignments = []
        
        # Create 3 demo classes for today
        time_slots = [
            (time(9, 0), time(10, 0)),
            (time(10, 30), time(11, 30)),
            (time(13, 0), time(14, 0)),
        ]
        
        for i, (start_time, end_time) in enumerate(time_slots):
            if i < len(assignments):
                TeacherSchedule.objects.create(
                    teacher=teacher,
                    subject_assignment=assignments[i],
                    day_of_week=weekday,
                    start_time=start_time,
                    end_time=end_time,
                    classroom=f"Room {200 + i}",
                    is_active=True
                )
    
    def create_demo_sessions(self, teacher, today, num_sessions):
        """Create demo attendance sessions"""
        schedules = TeacherSchedule.objects.filter(
            teacher=teacher,
            day_of_week=today.weekday(),
            is_active=True
        ).order_by('start_time')[:num_sessions]
        
        for schedule in schedules:
            AttendanceSession.objects.create(
                teacher_assignment=schedule.subject_assignment,
                date=today,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                topic_covered=f'Demo lesson for {schedule.subject_assignment.subject.name}',
                is_completed=True
            )
    
    def create_enhanced_attendance(self, teacher, today, activities, classes_attended, classes_scheduled):
        """Create enhanced attendance record with all activities"""
        # Create activity logs with proper prioritization
        for activity_time, activity_type, description in activities:
            # Auto-assign priority
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
        
        # Create enhanced attendance record
        first_activity_time = activities[0][0]
        last_activity_time = activities[-1][0]
        
        attendance = TeacherAttendance.objects.create(
            teacher=teacher,
            date=today,
            first_activity_time=first_activity_time,
            last_activity_time=last_activity_time,
            check_in_time=first_activity_time.time(),
            check_out_time=last_activity_time.time(),
            classes_scheduled=classes_scheduled,
            classes_attended=classes_attended,
            validation_method='schedule_based',
            location_verified=True,
            is_auto_marked=True
        )
        
        # Calculate all enhanced metrics
        attendance.calculate_scheduled_hours()
        attendance.calculate_hours()
        attendance.calculate_attendance_percentage()
        attendance.determine_status_advanced()
        attendance.save()
    
    def show_enhanced_results(self, today):
        """Show comprehensive results of enhanced system"""
        self.stdout.write('\n📊 ENHANCED ATTENDANCE RESULTS:')
        self.stdout.write('=' * 50)
        
        attendances = TeacherAttendance.objects.filter(date=today).select_related('teacher__user')
        
        for attendance in attendances:
            teacher_name = attendance.teacher.user.get_full_name()
            performance_score = attendance.get_performance_score()
            
            # Status with emoji
            status_emoji = {
                'present': '✅',
                'late': '⚠️',
                'absent': '❌',
                'partial': '🔶',
                'half_day': '🕐'
            }.get(attendance.status, '❓')
            
            self.stdout.write(f'\n{status_emoji} {teacher_name}')
            self.stdout.write(f'   📊 Performance Score: {performance_score}/100')
            self.stdout.write(f'   📈 Status: {attendance.get_status_display()}')
            self.stdout.write(f'   ⏰ Hours Worked: {attendance.total_hours}/{attendance.scheduled_hours}')
            self.stdout.write(f'   📚 Classes: {attendance.classes_attended}/{attendance.classes_scheduled}')
            self.stdout.write(f'   📋 Attendance Rate: {attendance.attendance_percentage:.1f}%')
            self.stdout.write(f'   🎯 Validation: {attendance.get_validation_method_display()}')
            self.stdout.write(f'   📍 Location Verified: {"Yes" if attendance.location_verified else "No"}')
            
            # Activity breakdown
            activities = TeacherActivityLog.objects.filter(
                teacher=attendance.teacher,
                timestamp__date=today
            )
            
            high_activities = activities.filter(priority_level='high').count()
            medium_activities = activities.filter(priority_level='medium').count()
            low_activities = activities.filter(priority_level='low').count()
            
            self.stdout.write(f'   🎯 Activities: High({high_activities}) Medium({medium_activities}) Low({low_activities})')
            
            # Performance rating
            if performance_score >= 90:
                rating = "🌟 Excellent"
            elif performance_score >= 75:
                rating = "👍 Good"
            elif performance_score >= 60:
                rating = "⚠️ Needs Improvement"
            else:
                rating = "❌ Poor"
            
            self.stdout.write(f'   🏆 Rating: {rating}')
        
        # System summary
        if attendances.exists():
            avg_performance = sum(att.get_performance_score() for att in attendances) / attendances.count()
            self.stdout.write(f'\n📈 SYSTEM PERFORMANCE:')
            self.stdout.write(f'   📊 Average Score: {avg_performance:.1f}/100')
            self.stdout.write(f'   👥 Teachers Tracked: {attendances.count()}')
            self.stdout.write(f'   🎯 Automatic Validation: 100%')