from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from academic.models import SemesterEnrollment, Course, AcademicYear
from accounts.models import StudentProfile
import random

class Command(BaseCommand):
    help = 'Create sample semester enrollments for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of semester enrollments to create'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(self.style.SUCCESS(f'Creating {count} sample semester enrollments...'))
        
        # Get available data
        students = list(StudentProfile.objects.all())
        courses = list(Course.objects.all())
        academic_years = list(AcademicYear.objects.all())
        
        if not students:
            self.stdout.write(self.style.ERROR('No students found. Please create students first.'))
            return
        
        if not courses:
            self.stdout.write(self.style.ERROR('No courses found. Please create courses first.'))
            return
        
        if not academic_years:
            self.stdout.write(self.style.ERROR('No academic years found. Please create academic years first.'))
            return
        
        # Status choices
        status_choices = ['pending', 'approved', 'completed', 'rejected']
        sections = ['A', 'B', 'C', 'D']
        
        created_count = 0
        
        for i in range(count):
            # Random selections
            student = random.choice(students)
            course = random.choice(courses)
            academic_year = random.choice(academic_years)
            year = random.randint(1, 4)
            semester = random.randint(1, 8)
            section = random.choice(sections)
            status = random.choice(status_choices)
            
            # Check if enrollment already exists
            existing = SemesterEnrollment.objects.filter(
                student=student,
                course=course,
                year=year,
                semester=semester,
                academic_year=academic_year
            ).first()
            
            if existing:
                continue  # Skip if already exists
            
            # Create enrollment
            enrollment = SemesterEnrollment.objects.create(
                student=student,
                course=course,
                year=year,
                semester=semester,
                academic_year=academic_year,
                section=section,
                enrollment_status=status,
                enrollment_fee_amount=random.choice([None, 500.00, 750.00, 1000.00]),
                enrollment_fee_paid=random.choice([True, False]),
                enrollment_deadline=timezone.now().date() + timedelta(days=random.randint(30, 90)),
                is_active=True
            )
            
            # If approved or completed, set approval details
            if status in ['approved', 'completed']:
                enrollment.approved_date = timezone.now() - timedelta(days=random.randint(1, 30))
                enrollment.save()
            
            created_count += 1
            
            self.stdout.write(
                f'Created enrollment: {student.user.get_full_name()} - {course.name} - Year {year}, Sem {semester}'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} semester enrollments!')
        )
        
        # Display statistics
        self.stdout.write('\n--- Enrollment Statistics ---')
        
        total_enrollments = SemesterEnrollment.objects.count()
        self.stdout.write(f'Total Semester Enrollments: {total_enrollments}')
        
        for status_code, status_name in SemesterEnrollment.ENROLLMENT_STATUS_CHOICES:
            count = SemesterEnrollment.objects.filter(enrollment_status=status_code).count()
            if count > 0:
                self.stdout.write(f'{status_name}: {count}')
        
        # Semester distribution
        self.stdout.write('\n--- Semester Distribution ---')
        for semester in range(1, 9):
            count = SemesterEnrollment.objects.filter(semester=semester).count()
            if count > 0:
                self.stdout.write(f'Semester {semester}: {count} enrollments')
        
        # Year distribution
        self.stdout.write('\n--- Year Distribution ---')
        for year in range(1, 5):
            count = SemesterEnrollment.objects.filter(year=year).count()
            if count > 0:
                self.stdout.write(f'Year {year}: {count} enrollments')