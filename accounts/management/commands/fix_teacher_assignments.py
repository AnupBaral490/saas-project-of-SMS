"""
Management command to fix and create teacher assignments
"""
from django.core.management.base import BaseCommand
from accounts.models import User, TeacherProfile
from academic.models import TeacherSubjectAssignment, Subject, Class


class Command(BaseCommand):
    help = 'Fix teacher assignments and ensure all classes have teachers'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('FIXING TEACHER ASSIGNMENTS'))
        self.stdout.write('='*70)

        # Get all teacher assignments with missing teacher info
        assignments = TeacherSubjectAssignment.objects.all().select_related('teacher__user', 'subject', 'class_assigned')
        
        fixed_count = 0
        for assignment in assignments:
            if not assignment.teacher or not assignment.teacher.user.first_name:
                self.stdout.write(self.style.WARNING(f'\n⚠️  Found assignment with incomplete teacher: {assignment}'))
                
                # Try to find a valid teacher
                valid_teachers = TeacherProfile.objects.filter(
                    user__first_name__isnull=False
                ).exclude(user__first_name='')
                
                if valid_teachers.exists():
                    # Assign to first valid teacher
                    assignment.teacher = valid_teachers.first()
                    assignment.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Fixed: Assigned to {assignment.teacher.user.get_full_name()}'))
                    fixed_count += 1
        
        # Check for classes without teachers
        all_classes = Class.objects.all()
        self.stdout.write(f'\n\nChecking {all_classes.count()} classes for teacher assignments...')
        
        for class_obj in all_classes:
            assignments = TeacherSubjectAssignment.objects.filter(class_assigned=class_obj)
            
            if not assignments.exists():
                self.stdout.write(self.style.WARNING(f'\n⚠️  Class has no teachers: {class_obj}'))
                
                # Get subjects for this class
                subjects = Subject.objects.filter(
                    course=class_obj.course,
                    year=class_obj.year,
                    semester=class_obj.semester
                )
                
                if subjects.exists():
                    # Get a teacher
                    teachers = TeacherProfile.objects.filter(
                        user__first_name__isnull=False
                    ).exclude(user__first_name='')
                    
                    if teachers.exists():
                        teacher = teachers.first()
                        
                        # Create assignments for each subject
                        for subject in subjects:
                            # Check if assignment already exists
                            existing = TeacherSubjectAssignment.objects.filter(
                                teacher=teacher,
                                subject=subject,
                                class_assigned=class_obj
                            ).exists()
                            
                            if not existing:
                                TeacherSubjectAssignment.objects.create(
                                    teacher=teacher,
                                    subject=subject,
                                    class_assigned=class_obj,
                                    academic_year=class_obj.academic_year
                                )
                                self.stdout.write(self.style.SUCCESS(
                                    f'  ✓ Created: {teacher.user.get_full_name()} → {subject.name} → {class_obj}'
                                ))
                                fixed_count += 1
        
        self.stdout.write('\n' + '='*70)
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ Fixed/Created {fixed_count} teacher assignments'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ All teacher assignments are properly configured'))
        self.stdout.write('='*70 + '\n')
