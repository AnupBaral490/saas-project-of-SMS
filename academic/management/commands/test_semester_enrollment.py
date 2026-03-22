from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from academic.models import StudentEnrollment, Department, Course, Class
from accounts.models import StudentProfile

class Command(BaseCommand):
    help = 'Test semester-wise enrollment functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Semester-wise Enrollment Functionality'))
        
        # Test 1: Check total enrollments
        total_enrollments = StudentEnrollment.objects.count()
        active_enrollments = StudentEnrollment.objects.filter(is_active=True).count()
        
        self.stdout.write(f'Total Enrollments: {total_enrollments}')
        self.stdout.write(f'Active Enrollments: {active_enrollments}')
        
        # Test 2: Check semester-wise distribution
        self.stdout.write('\n--- Semester-wise Distribution ---')
        for semester in range(1, 9):
            semester_count = StudentEnrollment.objects.filter(
                class_enrolled__semester=semester,
                is_active=True
            ).count()
            if semester_count > 0:
                self.stdout.write(f'Semester {semester}: {semester_count} students')
        
        # Test 3: Check year-wise distribution
        self.stdout.write('\n--- Year-wise Distribution ---')
        for year in range(1, 5):
            year_count = StudentEnrollment.objects.filter(
                class_enrolled__year=year,
                is_active=True
            ).count()
            if year_count > 0:
                self.stdout.write(f'Year {year}: {year_count} students')
        
        # Test 4: Check department-wise distribution
        self.stdout.write('\n--- Department-wise Distribution ---')
        departments = Department.objects.all()
        for dept in departments:
            dept_count = StudentEnrollment.objects.filter(
                class_enrolled__course__department=dept,
                is_active=True
            ).count()
            if dept_count > 0:
                self.stdout.write(f'{dept.name} ({dept.code}): {dept_count} students')
        
        # Test 5: Check for students with multiple semester enrollments
        self.stdout.write('\n--- Students with Multiple Semester Enrollments ---')
        students_with_multiple = StudentProfile.objects.annotate(
            enrollment_count=Count('studentenrollment', filter=Q(studentenrollment__is_active=True))
        ).filter(enrollment_count__gt=1)
        
        for student in students_with_multiple:
            enrollments = StudentEnrollment.objects.filter(
                student=student,
                is_active=True
            ).select_related('class_enrolled')
            
            enrollment_info = []
            for enrollment in enrollments:
                enrollment_info.append(
                    f"Year {enrollment.class_enrolled.year}, Sem {enrollment.class_enrolled.semester}"
                )
            
            self.stdout.write(
                f'{student.user.get_full_name()} ({student.student_id}): {", ".join(enrollment_info)}'
            )
        
        # Test 6: Semester-wise course distribution
        self.stdout.write('\n--- Semester-wise Course Distribution ---')
        semester_course_data = {}
        
        enrollments = StudentEnrollment.objects.filter(is_active=True).select_related(
            'class_enrolled__course', 'class_enrolled'
        )
        
        for enrollment in enrollments:
            semester = enrollment.class_enrolled.semester
            year = enrollment.class_enrolled.year
            course = enrollment.class_enrolled.course.name
            
            key = f"Year {year} - Semester {semester}"
            if key not in semester_course_data:
                semester_course_data[key] = {}
            
            if course not in semester_course_data[key]:
                semester_course_data[key][course] = 0
            
            semester_course_data[key][course] += 1
        
        for semester_key, courses in sorted(semester_course_data.items()):
            self.stdout.write(f'\n{semester_key}:')
            for course, count in courses.items():
                self.stdout.write(f'  - {course}: {count} students')
        
        self.stdout.write(self.style.SUCCESS('\nSemester-wise enrollment test completed successfully!'))