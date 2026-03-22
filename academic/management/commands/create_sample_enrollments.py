from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from accounts.models import User, StudentProfile
from academic.models import (
    AcademicYear, Department, Course, Subject, Class, StudentEnrollment
)

class Command(BaseCommand):
    help = 'Create sample enrollment data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--students',
            type=int,
            default=20,
            help='Number of sample students to create and enroll'
        )

    def handle(self, *args, **options):
        num_students = options['students']
        
        with transaction.atomic():
            # Create or get current academic year
            current_year, created = AcademicYear.objects.get_or_create(
                year="2025-2026",
                defaults={
                    'start_date': date(2025, 8, 1),
                    'end_date': date(2026, 7, 31),
                    'is_current': True
                }
            )
            if created:
                self.stdout.write(f"Created academic year: {current_year.year}")
            
            # Create departments if they don't exist
            departments_data = [
                {'name': 'Computer Science', 'code': 'CS', 'description': 'Department of Computer Science and Information Technology'},
                {'name': 'Business Administration', 'code': 'BA', 'description': 'Department of Business Administration and Management'},
                {'name': 'Information Management', 'code': 'BIM', 'description': 'Bachelor in Information Management'},
                {'name': 'Engineering', 'code': 'ENG', 'description': 'Department of Engineering'},
            ]
            
            departments = []
            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    code=dept_data['code'],
                    defaults=dept_data
                )
                departments.append(dept)
                if created:
                    self.stdout.write(f"Created department: {dept.name}")
            
            # Create courses if they don't exist
            courses_data = [
                {'name': 'Bachelor of Science in Computer Science', 'code': 'BSCS', 'department': departments[0], 'duration_years': 4},
                {'name': 'Business Analytics', 'code': 'BA', 'department': departments[1], 'duration_years': 4},
                {'name': 'BIM-8th Semester', 'code': 'BIM8', 'department': departments[2], 'duration_years': 4},
                {'name': 'Software Engineering', 'code': 'SE', 'department': departments[0], 'duration_years': 4},
                {'name': 'Data Science', 'code': 'DS', 'department': departments[0], 'duration_years': 4},
            ]
            
            courses = []
            for course_data in courses_data:
                course, created = Course.objects.get_or_create(
                    code=course_data['code'],
                    defaults=course_data
                )
                courses.append(course)
                if created:
                    self.stdout.write(f"Created course: {course.name}")
            
            # Create classes for each course
            classes = []
            for course in courses:
                for year in range(1, min(course.duration_years + 1, 5)):  # Max 4 years
                    for semester in [1, 2]:
                        for section in ['A', 'B']:
                            class_obj, created = Class.objects.get_or_create(
                                course=course,
                                year=year,
                                semester=semester,
                                section=section,
                                academic_year=current_year,
                                defaults={
                                    'name': f"{course.name} - Year {year}, Sem {semester} - {section}"
                                }
                            )
                            classes.append(class_obj)
                            if created:
                                self.stdout.write(f"Created class: {class_obj.name}")
            
            # Create sample subjects for each course
            subjects_data = {
                'BSCS': [
                    {'name': 'Programming Fundamentals', 'code': 'CS101', 'year': 1, 'semester': 1, 'credits': 3},
                    {'name': 'Data Structures', 'code': 'CS201', 'year': 2, 'semester': 1, 'credits': 4},
                    {'name': 'Database Systems', 'code': 'CS301', 'year': 3, 'semester': 1, 'credits': 3},
                    {'name': 'Software Engineering', 'code': 'CS401', 'year': 4, 'semester': 1, 'credits': 4},
                ],
                'BA': [
                    {'name': 'Business Statistics', 'code': 'BA101', 'year': 1, 'semester': 1, 'credits': 3},
                    {'name': 'Marketing Analytics', 'code': 'BA201', 'year': 2, 'semester': 1, 'credits': 3},
                    {'name': 'Financial Analysis', 'code': 'BA301', 'year': 3, 'semester': 1, 'credits': 4},
                ],
                'BIM8': [
                    {'name': 'Information Systems', 'code': 'BIM101', 'year': 1, 'semester': 1, 'credits': 3},
                    {'name': 'Project Management', 'code': 'BIM401', 'year': 4, 'semester': 8, 'credits': 4},
                ],
            }
            
            for course in courses:
                if course.code in subjects_data:
                    for subject_data in subjects_data[course.code]:
                        subject_data['course'] = course
                        subject, created = Subject.objects.get_or_create(
                            code=subject_data['code'],
                            defaults=subject_data
                        )
                        if created:
                            self.stdout.write(f"Created subject: {subject.name}")
            
            # Create sample students and enroll them
            students_created = 0
            enrollments_created = 0
            
            for i in range(num_students):
                # Create user
                username = f"student{i+1:03d}"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': f'Student',
                        'last_name': f'User {i+1:03d}',
                        'email': f'{username}@example.com',
                        'user_type': 'student',
                        'is_active': True
                    }
                )
                
                if created:
                    user.set_password('password123')
                    user.save()
                    students_created += 1
                
                # Create student profile
                student_profile, profile_created = StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'student_id': f'STU{i+1:06d}',
                        'admission_date': date.today() - timedelta(days=30),
                        'guardian_name': f'Guardian of {user.get_full_name()}',
                        'guardian_phone': f'+1234567{i+1:03d}',
                        'guardian_email': f'guardian{i+1:03d}@example.com',
                        'emergency_contact': f'+1234567{i+1:03d}',
                        'blood_group': 'O+'
                    }
                )
                
                # Enroll student in a random class
                if classes:
                    import random
                    selected_class = random.choice(classes)
                    
                    enrollment, enrollment_created = StudentEnrollment.objects.get_or_create(
                        student=student_profile,
                        class_enrolled=selected_class,
                        defaults={
                            'is_active': True
                        }
                    )
                    
                    if enrollment_created:
                        enrollments_created += 1
                        self.stdout.write(
                            f"Enrolled {user.get_full_name()} in {selected_class}"
                        )
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSample data creation completed!\n'
                    f'Students created: {students_created}\n'
                    f'Enrollments created: {enrollments_created}\n'
                    f'Departments: {len(departments)}\n'
                    f'Courses: {len(courses)}\n'
                    f'Classes: {len(classes)}\n'
                    f'Academic Year: {current_year.year}'
                )
            )
            
            # Show enrollment summary by course
            self.stdout.write('\nEnrollment Summary by Course:')
            for course in courses:
                enrollment_count = StudentEnrollment.objects.filter(
                    class_enrolled__course=course,
                    is_active=True
                ).count()
                self.stdout.write(f'  {course.name}: {enrollment_count} students')