from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time
from accounts.models import TeacherProfile, StudentProfile
from academic.models import Assignment, AssignmentSubmission, TeacherSubjectAssignment, StudentEnrollment
from attendance.models import AttendanceSession, AttendanceRecord
import random

class Command(BaseCommand):
    help = 'Create sample data for teacher dashboard testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--teacher-username',
            type=str,
            help='Username of the teacher to create data for',
            default=None
        )

    def handle(self, *args, **options):
        teacher_username = options.get('teacher_username')
        
        if teacher_username:
            try:
                teacher = TeacherProfile.objects.get(user__username=teacher_username)
                self.stdout.write(f"Creating sample data for teacher: {teacher.user.get_full_name()}")
            except TeacherProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Teacher with username '{teacher_username}' not found"))
                return
        else:
            # Get the first teacher
            teacher = TeacherProfile.objects.first()
            if not teacher:
                self.stdout.write(self.style.ERROR("No teachers found in the database"))
                return
            self.stdout.write(f"Creating sample data for teacher: {teacher.user.get_full_name()}")

        # Get teacher assignments
        teacher_assignments = TeacherSubjectAssignment.objects.filter(teacher=teacher)
        
        if not teacher_assignments.exists():
            self.stdout.write(self.style.WARNING("No teacher assignments found. Please assign subjects to the teacher first."))
            return

        created_assignments = 0
        created_submissions = 0
        created_sessions = 0
        created_attendance = 0

        for assignment in teacher_assignments:
            class_obj = assignment.class_assigned
            subject = assignment.subject
            
            # Get students in this class
            students = StudentProfile.objects.filter(
                studentenrollment__class_enrolled=class_obj,
                studentenrollment__is_active=True
            )
            
            if not students.exists():
                self.stdout.write(f"No students found in class {class_obj.name}")
                continue

            # Create 2-3 assignments for each class
            for i in range(random.randint(2, 4)):
                assignment_obj = Assignment.objects.create(
                    title=f"{subject.name} Assignment {i+1}",
                    description=f"Sample assignment {i+1} for {subject.name}",
                    assignment_type='homework',
                    subject=subject,
                    class_assigned=class_obj,
                    teacher=teacher,
                    due_date=timezone.now() + timezone.timedelta(days=random.randint(1, 30)),
                    max_marks=100
                )
                created_assignments += 1

                # Create submissions for 60-90% of students
                submission_rate = random.uniform(0.6, 0.9)
                students_to_submit = random.sample(
                    list(students), 
                    int(len(students) * submission_rate)
                )

                for student in students_to_submit:
                    marks = random.randint(40, 95)  # Random marks between 40-95
                    AssignmentSubmission.objects.create(
                        assignment=assignment_obj,
                        student=student,
                        submission_text=f"Sample submission by {student.user.get_full_name()}",
                        marks_obtained=marks,
                        graded_by=teacher,
                        graded_at=timezone.now()
                    )
                    created_submissions += 1

            # Create 5-10 attendance sessions
            for i in range(random.randint(5, 10)):
                session_date = timezone.now().date() - timezone.timedelta(days=random.randint(1, 30))
                start_hour = 9 + random.randint(0, 6)
                start_minute = random.choice([0, 30])
                start_time = time(start_hour, start_minute)
                
                # Calculate end time (1.5 hours later)
                end_hour = start_hour + 1
                end_minute = start_minute + 30
                if end_minute >= 60:
                    end_hour += 1
                    end_minute -= 60
                end_time = time(min(end_hour, 23), end_minute)
                
                # Check if session already exists
                existing_session = AttendanceSession.objects.filter(
                    teacher_assignment=assignment,
                    date=session_date,
                    start_time=start_time
                ).first()
                
                if existing_session:
                    session = existing_session
                else:
                    session = AttendanceSession.objects.create(
                        teacher_assignment=assignment,
                        date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        topic_covered=f"Topic {i+1} - {subject.name}",
                        is_completed=True
                    )
                    created_sessions += 1

                # Create attendance records for students
                for student in students:
                    # Check if attendance record already exists
                    existing_record = AttendanceRecord.objects.filter(
                        session=session,
                        student=student
                    ).first()
                    
                    if not existing_record:
                        # 80-95% attendance rate
                        if random.random() < random.uniform(0.8, 0.95):
                            status = random.choices(
                                ['present', 'late'], 
                                weights=[0.9, 0.1]
                            )[0]
                        else:
                            status = random.choices(
                                ['absent', 'excused'], 
                                weights=[0.8, 0.2]
                            )[0]

                        AttendanceRecord.objects.create(
                            session=session,
                            student=student,
                            status=status
                        )
                        created_attendance += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample data created successfully!\n"
                f"- Assignments: {created_assignments}\n"
                f"- Submissions: {created_submissions}\n"
                f"- Attendance Sessions: {created_sessions}\n"
                f"- Attendance Records: {created_attendance}"
            )
        )