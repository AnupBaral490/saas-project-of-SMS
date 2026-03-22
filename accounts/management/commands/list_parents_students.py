"""
Management command to list all parents and students
Usage: python manage.py list_parents_students
"""

from django.core.management.base import BaseCommand
from accounts.models import User, ParentProfile, StudentProfile


class Command(BaseCommand):
    help = 'List all parents and students with their current relationships'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('PARENTS'))
        self.stdout.write('='*70)

        parents = User.objects.filter(user_type='parent').order_by('username')
        
        if not parents.exists():
            self.stdout.write(self.style.WARNING('No parent users found'))
        else:
            for parent in parents:
                full_name = parent.get_full_name() or 'No name set'
                self.stdout.write(f'\n📋 Username: {parent.username}')
                self.stdout.write(f'   Name: {full_name}')
                self.stdout.write(f'   Email: {parent.email or "Not set"}')
                
                try:
                    parent_profile = parent.parent_profile
                    children = parent_profile.children.all()
                    
                    if children.exists():
                        self.stdout.write(self.style.SUCCESS(f'   Children: {children.count()}'))
                        for child in children:
                            self.stdout.write(f'      → {child.user.get_full_name() or child.user.username} ({child.student_id})')
                    else:
                        self.stdout.write(self.style.WARNING('   Children: None linked'))
                        
                except ParentProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR('   ⚠️  Parent profile missing'))

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('STUDENTS'))
        self.stdout.write('='*70)

        students = User.objects.filter(user_type='student').order_by('username')
        
        if not students.exists():
            self.stdout.write(self.style.WARNING('No student users found'))
        else:
            for student in students:
                full_name = student.get_full_name() or 'No name set'
                self.stdout.write(f'\n👤 Username: {student.username}')
                self.stdout.write(f'   Name: {full_name}')
                self.stdout.write(f'   Email: {student.email or "Not set"}')
                
                try:
                    student_profile = student.student_profile
                    self.stdout.write(f'   Student ID: {student_profile.student_id}')
                    
                    # Check if this student has parents
                    parents_linked = student_profile.parents.all()
                    if parents_linked.exists():
                        self.stdout.write(self.style.SUCCESS(f'   Parents: {parents_linked.count()}'))
                        for parent_prof in parents_linked:
                            self.stdout.write(f'      → {parent_prof.user.get_full_name() or parent_prof.user.username}')
                    else:
                        self.stdout.write(self.style.WARNING('   Parents: None linked'))
                        
                    # Check enrollment
                    enrollment = student_profile.get_current_enrollment()
                    if enrollment:
                        self.stdout.write(f'   Enrolled: {enrollment.class_enrolled}')
                    else:
                        self.stdout.write(self.style.WARNING('   Enrolled: No'))
                        
                except StudentProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR('   ⚠️  Student profile missing'))

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*70)
        self.stdout.write(f'Total Parents: {parents.count()}')
        self.stdout.write(f'Total Students: {students.count()}')
        
        # Count linked relationships
        linked_students = 0
        for parent in parents:
            try:
                linked_students += parent.parent_profile.children.count()
            except ParentProfile.DoesNotExist:
                pass
        
        self.stdout.write(f'Total Parent-Child Links: {linked_students}')
        self.stdout.write('\n' + '='*70 + '\n')
