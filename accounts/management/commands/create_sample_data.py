from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime, timedelta
from accounts.models import StudentProfile, TeacherProfile, AdminProfile, ParentProfile
from academic.models import (
    AcademicYear, Department, Course, Subject, Class, 
    StudentEnrollment, TeacherSubjectAssignment, Assignment
)
from attendance.models import AttendanceSession, AttendanceRecord
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create comprehensive sample data for the Student Management System'

    def handle(self, *args, **options):
        self.stdout.write('Creating comprehensive sample data...')
        
        # Create Academic Year
        current_year = AcademicYear.objects.create(
            year="2023-2024",
            start_date=date(2023, 8, 1),
            end_date=date(2024, 7, 31),
            is_current=True
        )
        self.stdout.write(self.style.SUCCESS('Academic year created'))
        
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@sms.com',
                password='admin123',
                first_name='System',
                last_name='Administrator',
                user_type='admin'
            )
            AdminProfile.objects.create(
                user=admin_user,
                employee_id='ADM000001',
                department='Administration'
            )
            self.stdout.write(self.style.SUCCESS('Admin user created'))

        # Create Departments
        cs_dept = Department.objects.create(
            name='Computer Science',
            code='CS',
            description='Department of Computer Science and Engineering'
        )
        
        math_dept = Department.objects.create(
            name='Mathematics',
            code='MATH',
            description='Department of Mathematics'
        )
        
        eng_dept = Department.objects.create(
            name='English',
            code='ENG',
            description='Department of English Literature'
        )
        
        self.stdout.write(self.style.SUCCESS('Departments created'))

        # Create Courses
        bscs_course = Course.objects.create(
            name='Bachelor of Science in Computer Science',
            code='BSCS',
            department=cs_dept,
            duration_years=4,
            description='4-year undergraduate program in Computer Science'
        )
        
        bsmath_course = Course.objects.create(
            name='Bachelor of Science in Mathematics',
            code='BSMATH',
            department=math_dept,
            duration_years=4,
            description='4-year undergraduate program in Mathematics'
        )
        
        self.stdout.write(self.style.SUCCESS('Courses created'))

        # Create Subjects
        subjects_data = [
            # Year 1, Semester 1
            ('Programming Fundamentals', 'CS101', bscs_course, 1, 1, 4),
            ('Calculus I', 'MATH101', bscs_course, 1, 1, 3),
            ('English Composition', 'ENG101', bscs_course, 1, 1, 3),
            
            # Year 1, Semester 2
            ('Object Oriented Programming', 'CS102', bscs_course, 1, 2, 4),
            ('Calculus II', 'MATH102', bscs_course, 1, 2, 3),
            ('Physics I', 'PHY101', bscs_course, 1, 2, 3),
            
            # Year 2, Semester 1
            ('Data Structures', 'CS201', bscs_course, 2, 1, 4),
            ('Database Systems', 'CS202', bscs_course, 2, 1, 4),
            ('Discrete Mathematics', 'MATH201', bscs_course, 2, 1, 3),
            
            # Year 2, Semester 2
            ('Web Development', 'CS203', bscs_course, 2, 2, 4),
            ('Software Engineering', 'CS204', bscs_course, 2, 2, 4),
            ('Statistics', 'MATH202', bscs_course, 2, 2, 3),
        ]
        
        subjects = []
        for name, code, course, year, semester, credits in subjects_data:
            subject = Subject.objects.create(
                name=name,
                code=code,
                course=course,
                year=year,
                semester=semester,
                credits=credits
            )
            subjects.append(subject)
        
        self.stdout.write(self.style.SUCCESS('Subjects created'))

        # Create Teachers
        teachers_data = [
            ('john.smith', 'john.smith@sms.com', 'John', 'Smith', 'Dr.', 'Ph.D Computer Science', 8, 'Database Systems'),
            ('jane.doe', 'jane.doe@sms.com', 'Jane', 'Doe', 'Prof.', 'M.Sc Software Engineering', 12, 'Web Development'),
            ('mike.wilson', 'mike.wilson@sms.com', 'Mike', 'Wilson', 'Dr.', 'Ph.D Mathematics', 10, 'Mathematics'),
            ('sarah.brown', 'sarah.brown@sms.com', 'Sarah', 'Brown', 'Ms.', 'M.Sc Computer Science', 6, 'Programming'),
            ('david.jones', 'david.jones@sms.com', 'David', 'Jones', 'Dr.', 'Ph.D Software Engineering', 15, 'Software Engineering'),
        ]
        
        teachers = []
        for username, email, first_name, last_name, title, qualification, experience, specialization in teachers_data:
            if not User.objects.filter(username=username).exists():
                teacher_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='teacher123',
                    first_name=first_name,
                    last_name=last_name,
                    user_type='teacher'
                )
                teacher_profile = TeacherProfile.objects.create(
                    user=teacher_user,
                    employee_id=f"EMP{teacher_user.id:06d}",
                    qualification=qualification,
                    experience_years=experience,
                    specialization=specialization,
                    joining_date=date.today() - timedelta(days=experience*365)
                )
                teachers.append(teacher_profile)
        
        self.stdout.write(self.style.SUCCESS('Teachers created'))

        # Create Classes
        classes_data = [
            ('CS Year 1 Semester 1 Section A', bscs_course, 1, 1, 'A'),
            ('CS Year 1 Semester 2 Section A', bscs_course, 1, 2, 'A'),
            ('CS Year 2 Semester 1 Section A', bscs_course, 2, 1, 'A'),
            ('CS Year 2 Semester 2 Section A', bscs_course, 2, 2, 'A'),
        ]
        
        classes = []
        for name, course, year, semester, section in classes_data:
            class_obj = Class.objects.create(
                name=name,
                course=course,
                year=year,
                semester=semester,
                section=section,
                academic_year=current_year,
                class_teacher=random.choice(teachers) if teachers else None
            )
            classes.append(class_obj)
        
        self.stdout.write(self.style.SUCCESS('Classes created'))

        # Create Students
        students_data = [
            ('alice.johnson', 'alice.johnson@student.sms.com', 'Alice', 'Johnson', 'Robert Johnson', '+1234567890'),
            ('bob.smith', 'bob.smith@student.sms.com', 'Bob', 'Smith', 'Mary Smith', '+1234567891'),
            ('charlie.brown', 'charlie.brown@student.sms.com', 'Charlie', 'Brown', 'John Brown', '+1234567892'),
            ('diana.wilson', 'diana.wilson@student.sms.com', 'Diana', 'Wilson', 'Lisa Wilson', '+1234567893'),
            ('edward.davis', 'edward.davis@student.sms.com', 'Edward', 'Davis', 'Michael Davis', '+1234567894'),
            ('fiona.miller', 'fiona.miller@student.sms.com', 'Fiona', 'Miller', 'Sarah Miller', '+1234567895'),
            ('george.taylor', 'george.taylor@student.sms.com', 'George', 'Taylor', 'David Taylor', '+1234567896'),
            ('helen.anderson', 'helen.anderson@student.sms.com', 'Helen', 'Anderson', 'Jennifer Anderson', '+1234567897'),
            ('ivan.thomas', 'ivan.thomas@student.sms.com', 'Ivan', 'Thomas', 'William Thomas', '+1234567898'),
            ('julia.jackson', 'julia.jackson@student.sms.com', 'Julia', 'Jackson', 'Patricia Jackson', '+1234567899'),
        ]
        
        students = []
        for username, email, first_name, last_name, guardian_name, guardian_phone in students_data:
            if not User.objects.filter(username=username).exists():
                student_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='student123',
                    first_name=first_name,
                    last_name=last_name,
                    user_type='student'
                )
                student_profile = StudentProfile.objects.create(
                    user=student_user,
                    student_id=f"STU{student_user.id:06d}",
                    admission_date=date.today() - timedelta(days=random.randint(30, 365)),
                    guardian_name=guardian_name,
                    guardian_phone=guardian_phone,
                    guardian_email=f"{guardian_name.lower().replace(' ', '.')}@parent.com",
                    emergency_contact=guardian_phone
                )
                students.append(student_profile)
        
        self.stdout.write(self.style.SUCCESS('Students created'))

        # Enroll students in classes
        for i, student in enumerate(students):
            # Distribute students across different years/semesters
            if i < 3:  # First 3 students in Year 1 Sem 1
                class_to_enroll = classes[0]
            elif i < 6:  # Next 3 in Year 1 Sem 2
                class_to_enroll = classes[1]
            elif i < 8:  # Next 2 in Year 2 Sem 1
                class_to_enroll = classes[2]
            else:  # Rest in Year 2 Sem 2
                class_to_enroll = classes[3]
            
            StudentEnrollment.objects.create(
                student=student,
                class_enrolled=class_to_enroll,
                is_active=True
            )
        
        self.stdout.write(self.style.SUCCESS('Student enrollments created'))

        # Create Teacher Subject Assignments
        # Assign teachers to subjects based on their specialization
        assignments_data = [
            (teachers[0], subjects[7], classes[2]),  # John Smith - Database Systems
            (teachers[1], subjects[9], classes[3]),  # Jane Doe - Web Development
            (teachers[2], subjects[1], classes[0]),  # Mike Wilson - Calculus I
            (teachers[3], subjects[0], classes[0]),  # Sarah Brown - Programming Fundamentals
            (teachers[4], subjects[10], classes[3]), # David Jones - Software Engineering
        ]
        
        for teacher, subject, class_obj in assignments_data:
            if teacher and subject and class_obj:
                TeacherSubjectAssignment.objects.create(
                    teacher=teacher,
                    subject=subject,
                    class_assigned=class_obj,
                    academic_year=current_year
                )
        
        self.stdout.write(self.style.SUCCESS('Teacher assignments created'))

        # Create some attendance sessions and records
        today = timezone.now().date()
        for i in range(5):  # Create 5 days of attendance
            session_date = today - timedelta(days=i)
            
            # Create sessions for different subjects
            for assignment in TeacherSubjectAssignment.objects.all()[:3]:
                session = AttendanceSession.objects.create(
                    teacher_assignment=assignment,
                    date=session_date,
                    start_time=datetime.strptime('09:00', '%H:%M').time(),
                    end_time=datetime.strptime('10:30', '%H:%M').time(),
                    topic_covered=f"Topic {i+1} - {assignment.subject.name}",
                    is_completed=True
                )
                
                # Mark attendance for students in this class
                enrollments = StudentEnrollment.objects.filter(
                    class_enrolled=assignment.class_assigned,
                    is_active=True
                )
                
                for enrollment in enrollments:
                    # Random attendance status (mostly present)
                    status = random.choices(
                        ['present', 'absent', 'late', 'excused'],
                        weights=[80, 10, 8, 2]
                    )[0]
                    
                    AttendanceRecord.objects.create(
                        session=session,
                        student=enrollment.student,
                        status=status,
                        remarks=f"Auto-generated for {session_date}"
                    )
        
        self.stdout.write(self.style.SUCCESS('Attendance records created'))

        # Create some assignments
        assignment_titles = [
            "Database Design Project",
            "Web Application Development",
            "Data Structures Implementation",
            "Software Requirements Analysis",
            "Programming Exercise - Loops and Functions"
        ]
        
        for i, title in enumerate(assignment_titles):
            if i < len(TeacherSubjectAssignment.objects.all()):
                assignment_obj = TeacherSubjectAssignment.objects.all()[i]
                Assignment.objects.create(
                    title=title,
                    description=f"Complete the {title.lower()} as per the given requirements.",
                    assignment_type='project' if 'Project' in title else 'homework',
                    subject=assignment_obj.subject,
                    class_assigned=assignment_obj.class_assigned,
                    teacher=assignment_obj.teacher,
                    due_date=timezone.now() + timedelta(days=random.randint(7, 30)),
                    max_marks=100,
                    instructions="Follow the guidelines provided in class."
                )
        
        self.stdout.write(self.style.SUCCESS('Assignments created'))

        # Create Exam Types
        exam_types_data = [
            ('Quiz', 'Short assessment quiz', 10.00),
            ('Mid-term', 'Mid-semester examination', 30.00),
            ('Final', 'Final semester examination', 60.00),
            ('Assignment', 'Assignment evaluation', 20.00),
        ]
        
        from examination.models import ExamType, Examination, ExamResult
        
        exam_types = []
        for name, description, weightage in exam_types_data:
            exam_type, created = ExamType.objects.get_or_create(
                name=name,
                defaults={'description': description, 'weightage': weightage}
            )
            exam_types.append(exam_type)
        
        self.stdout.write(self.style.SUCCESS('Exam types created'))

        # Create Examinations
        examinations_data = [
            ('Database Systems - Final', exam_types[2], subjects[7], classes[2], date(2026, 2, 28), '09:00', '12:00', 100, 40),
            ('Web Development - Mid-term', exam_types[1], subjects[9], classes[3], date(2026, 2, 25), '10:00', '12:00', 100, 40),
            ('Software Engineering - Quiz', exam_types[0], subjects[10], classes[3], date(2026, 2, 20), '09:00', '10:00', 50, 20),
            ('Programming Fundamentals - Final', exam_types[2], subjects[0], classes[0], date(2026, 2, 15), '09:00', '12:00', 100, 40),
            ('Calculus I - Mid-term', exam_types[1], subjects[1], classes[0], date(2026, 2, 10), '14:00', '16:00', 80, 32),
        ]
        
        examinations = []
        for name, exam_type, subject, class_obj, exam_date, start_time, end_time, total_marks, passing_marks in examinations_data:
            # Find the teacher for this subject and class
            try:
                teacher_assignment = TeacherSubjectAssignment.objects.get(
                    subject=subject,
                    class_assigned=class_obj
                )
                teacher = teacher_assignment.teacher
            except TeacherSubjectAssignment.DoesNotExist:
                teacher = teachers[0] if teachers else None  # Fallback to first teacher
            
            if teacher:
                examination = Examination.objects.create(
                    name=name,
                    exam_type=exam_type,
                    subject=subject,
                    class_for=class_obj,
                    exam_date=exam_date,
                    start_time=datetime.strptime(start_time, '%H:%M').time(),
                    end_time=datetime.strptime(end_time, '%H:%M').time(),
                    total_marks=total_marks,
                    passing_marks=passing_marks,
                    instructions=f"Instructions for {name}. Please read all questions carefully.",
                    created_by=teacher
                )
                examinations.append(examination)
        
        self.stdout.write(self.style.SUCCESS('Examinations created'))

        # Create Exam Results
        for examination in examinations:
            # Get students enrolled in this examination's class
            enrollments = StudentEnrollment.objects.filter(
                class_enrolled=examination.class_for,
                is_active=True
            )
            
            for enrollment in enrollments:
                # Generate realistic marks (mostly passing grades)
                if examination.total_marks == 100:
                    marks_range = [85, 92, 78, 88, 76, 94, 82, 90, 74, 86]
                elif examination.total_marks == 80:
                    marks_range = [68, 74, 62, 70, 61, 75, 66, 72, 59, 69]
                else:  # 50 marks
                    marks_range = [42, 46, 39, 44, 38, 47, 41, 45, 37, 43]
                
                # Assign marks based on student index to ensure consistency
                student_index = list(enrollments).index(enrollment)
                if student_index < len(marks_range):
                    marks = marks_range[student_index]
                else:
                    marks = random.randint(int(examination.passing_marks), examination.total_marks)
                
                ExamResult.objects.create(
                    examination=examination,
                    student=enrollment.student,
                    marks_obtained=marks,
                    remarks=f"Good performance in {examination.name}" if marks >= examination.passing_marks else "Needs improvement",
                    entered_by=examination.created_by
                )
        
        self.stdout.write(self.style.SUCCESS('Exam results created'))

        self.stdout.write(self.style.SUCCESS('Comprehensive sample data created successfully!'))
        self.stdout.write(self.style.WARNING('Login credentials:'))
        self.stdout.write('Admin: admin / admin123')
        self.stdout.write('Teachers: john.smith, jane.doe, mike.wilson, sarah.brown, david.jones / teacher123')
        self.stdout.write('Students: alice.johnson, bob.smith, charlie.brown, etc. / student123')