from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from accounts.models import StudentProfile, TeacherProfile
from academic.models import TeacherSubjectAssignment, StudentEnrollment, AcademicYear
from attendance.models import AttendanceSession, AttendanceRecord
import random

class Command(BaseCommand):
    help = 'Create sample attendance sessions and records for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to create attendance for (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(f"Creating sample attendance data for {days} days...")
        
        # Get current academic year
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_year:
            self.stdout.write(self.style.ERROR('No current academic year found. Please create one first.'))
            return
        
        # Get teacher assignments
        assignments = TeacherSubjectAssignment.objects.filter(
            academic_year=current_year
        ).select_related('teacher', 'subject', 'class_assigned')
        
        if not assignments.exists():
            self.stdout.write(self.style.ERROR('No teacher assignments found. Please create some first.'))
            return
        
        # Get students with enrollments
        enrollments = StudentEnrollment.objects.filter(
            is_active=True,
            class_enrolled__academic_year=current_year
        ).select_related('student', 'class_enrolled')
        
        if not enrollments.exists():
            self.stdout.write(self.style.ERROR('No student enrollments found. Please create some first.'))
            return
        
        sessions_created = 0
        records_created = 0
        
        # Create attendance sessions for the past 'days' days
        start_date = timezone.now().date() - timedelta(days=days)
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Skip weekends
            if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            # Create 2-4 sessions per day for each assignment
            for assignment in assignments:
                num_sessions = random.randint(1, 3)  # 1-3 sessions per day per assignment
                
                for session_num in range(num_sessions):
                    # Create session at different times of day
                    hour = 9 + session_num * 2  # 9 AM, 11 AM, 1 PM, etc.
                    session_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                    
                    # Check if session already exists
                    existing_session = AttendanceSession.objects.filter(
                        teacher_assignment=assignment,
                        date=current_date,
                        start_time=session_time.time()
                    ).first()
                    
                    if existing_session:
                        session = existing_session
                    else:
                        session = AttendanceSession.objects.create(
                            teacher_assignment=assignment,
                            date=current_date,
                            start_time=session_time.time(),
                            end_time=(session_time + timedelta(hours=1)).time(),
                            topic_covered=f"Session {session_num + 1} - {assignment.subject.name}",
                            is_completed=True
                        )
                        sessions_created += 1
                    
                    # Get students for this class
                    class_enrollments = enrollments.filter(class_enrolled=assignment.class_assigned)
                    
                    # Create attendance records for students
                    for enrollment in class_enrollments:
                        # Check if record already exists
                        existing_record = AttendanceRecord.objects.filter(
                            session=session,
                            student=enrollment.student
                        ).first()
                        
                        if existing_record:
                            continue
                        
                        # Random attendance with realistic distribution
                        # 70% present, 15% late, 10% absent, 5% excused
                        rand = random.random()
                        if rand < 0.70:
                            status = 'present'
                        elif rand < 0.85:
                            status = 'late'
                        elif rand < 0.95:
                            status = 'absent'
                        else:
                            status = 'excused'
                        
                        AttendanceRecord.objects.create(
                            session=session,
                            student=enrollment.student,
                            status=status,
                            remarks=f"Auto-generated for {current_date}"
                        )
                        records_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {sessions_created} attendance sessions '
                f'and {records_created} attendance records for {days} days.'
            )
        )
        
        # Show some statistics
        total_sessions = AttendanceSession.objects.count()
        total_records = AttendanceRecord.objects.count()
        present_records = AttendanceRecord.objects.filter(status='present').count()
        late_records = AttendanceRecord.objects.filter(status='late').count()
        absent_records = AttendanceRecord.objects.filter(status='absent').count()
        excused_records = AttendanceRecord.objects.filter(status='excused').count()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ATTENDANCE STATISTICS:")
        self.stdout.write("="*50)
        self.stdout.write(f"Total Sessions: {total_sessions}")
        self.stdout.write(f"Total Records: {total_records}")
        self.stdout.write(f"Present: {present_records} ({present_records/total_records*100:.1f}%)")
        self.stdout.write(f"Late: {late_records} ({late_records/total_records*100:.1f}%)")
        self.stdout.write(f"Absent: {absent_records} ({absent_records/total_records*100:.1f}%)")
        self.stdout.write(f"Excused: {excused_records} ({excused_records/total_records*100:.1f}%)")
        
        overall_attendance = (present_records + late_records) / total_records * 100
        self.stdout.write(f"\nOverall Attendance Rate: {overall_attendance:.1f}%")