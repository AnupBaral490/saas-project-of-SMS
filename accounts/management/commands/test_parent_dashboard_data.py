"""
Management command to test parent dashboard data fetching
Usage: python manage.py test_parent_dashboard_data <parent_username>
"""

from django.core.management.base import BaseCommand
from accounts.models import User, ParentProfile, StudentProfile
from academic.models import StudentEnrollment, Subject
from attendance.models import AttendanceRecord
from examination.models import ExamResult


class Command(BaseCommand):
    help = 'Test parent dashboard data fetching for a specific parent'

    def add_arguments(self, parser):
        parser.add_argument('parent_username', type=str, help='Username of the parent')

    def handle(self, *args, **options):
        parent_username = options['parent_username']

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'TESTING PARENT DASHBOARD DATA FOR: {parent_username}'))
        self.stdout.write('='*70)

        # Get parent user
        try:
            parent_user = User.objects.get(username=parent_username, user_type='parent')
            self.stdout.write(self.style.SUCCESS(f'\n✓ Found parent user: {parent_user.get_full_name() or parent_username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'\n✗ Parent user "{parent_username}" not found'))
            return

        # Get parent profile
        try:
            parent_profile = parent_user.parent_profile
            self.stdout.write(self.style.SUCCESS(f'✓ Found parent profile'))
        except ParentProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Parent profile not found'))
            return

        # Get children
        children_profiles = parent_profile.children.all()
        self.stdout.write(f'\n📊 Children Count: {children_profiles.count()}')

        if children_profiles.count() == 0:
            self.stdout.write(self.style.WARNING('\n⚠️  No children linked to this parent!'))
            self.stdout.write('\nTo link children, run:')
            self.stdout.write(f'  python manage.py link_parent_child {parent_username} <child_username>')
            return

        # Process each child
        for idx, child in enumerate(children_profiles, 1):
            self.stdout.write('\n' + '-'*70)
            self.stdout.write(self.style.SUCCESS(f'CHILD #{idx}: {child.user.get_full_name() or child.user.username}'))
            self.stdout.write('-'*70)
            
            self.stdout.write(f'Username: {child.user.username}')
            self.stdout.write(f'Student ID: {child.student_id}')
            self.stdout.write(f'Email: {child.user.email or "Not set"}')

            # Check enrollment
            try:
                enrollment = child.get_current_enrollment()
                if enrollment:
                    self.stdout.write(self.style.SUCCESS(f'\n✓ Enrollment Found'))
                    self.stdout.write(f'  Class: {enrollment.class_enrolled}')
                    self.stdout.write(f'  Course: {enrollment.class_enrolled.course.name}')
                    self.stdout.write(f'  Year: {enrollment.class_enrolled.year}')
                    self.stdout.write(f'  Semester: {enrollment.class_enrolled.semester}')
                    self.stdout.write(f'  Section: {enrollment.class_enrolled.section}')
                    
                    # Get subjects
                    subjects = Subject.objects.filter(
                        course=enrollment.class_enrolled.course,
                        year=enrollment.class_enrolled.year,
                        semester=enrollment.class_enrolled.semester
                    )
                    self.stdout.write(f'\n📚 Subjects: {subjects.count()}')
                    for subject in subjects:
                        self.stdout.write(f'  - {subject.name} ({subject.code})')
                        
                        # Check exam results for this subject
                        results = ExamResult.objects.filter(
                            student=child,
                            examination__subject=subject
                        )
                        if results.exists():
                            latest_result = results.order_by('-examination__exam_date').first()
                            percentage = (float(latest_result.marks_obtained) / latest_result.examination.total_marks * 100)
                            self.stdout.write(f'    Grade: {latest_result.grade} ({percentage:.1f}%)')
                        else:
                            self.stdout.write(f'    Grade: Not graded yet')
                    
                else:
                    self.stdout.write(self.style.WARNING(f'\n⚠️  Not enrolled in any class'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n✗ Error checking enrollment: {e}'))

            # Check attendance
            try:
                attendance_records = AttendanceRecord.objects.filter(student=child)
                total_sessions = attendance_records.count()
                present_sessions = attendance_records.filter(status__in=['present', 'late']).count()
                attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
                
                self.stdout.write(f'\n📅 Attendance:')
                self.stdout.write(f'  Total Sessions: {total_sessions}')
                self.stdout.write(f'  Present: {present_sessions}')
                self.stdout.write(f'  Percentage: {attendance_percentage:.2f}%')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n✗ Error checking attendance: {e}'))

            # Check exam results
            try:
                all_results = ExamResult.objects.filter(student=child)
                self.stdout.write(f'\n📝 Exam Results: {all_results.count()}')
                
                if all_results.exists():
                    for result in all_results[:5]:  # Show first 5
                        self.stdout.write(f'  - {result.examination.name}: {result.marks_obtained}/{result.examination.total_marks} ({result.grade})')
                        
                    # Calculate GPA (using same method as student dashboard)
                    if all_results.exists():
                        # Grade point scale
                        grade_points = {
                            'A+': 4.0, 'A': 3.7, 'B+': 3.3, 'B': 3.0,
                            'C+': 2.3, 'C': 2.0, 'D': 1.0, 'F': 0.0
                        }
                        
                        # Weighted GPA calculation (based on exam total marks)
                        weighted_points_sum = 0
                        total_credits = 0
                        
                        for result in all_results:
                            grade_point = grade_points.get(result.grade, 0.0)
                            credit = result.examination.total_marks
                            weighted_points_sum += grade_point * credit
                            total_credits += credit
                        
                        gpa = (weighted_points_sum / total_credits) if total_credits > 0 else 0.0
                        gpa = round(gpa, 2)
                        self.stdout.write(f'\n  GPA: {gpa:.2f}/4.0')
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n✗ Error checking exam results: {e}'))

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('TEST COMPLETE'))
        self.stdout.write('='*70 + '\n')
