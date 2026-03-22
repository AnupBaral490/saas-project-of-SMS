"""
Management command to fix teacher names by setting first_name and last_name
from username if they are empty.
"""
from django.core.management.base import BaseCommand
from accounts.models import User, TeacherProfile


class Command(BaseCommand):
    help = 'Fix teacher names by setting first_name and last_name if empty'

    def handle(self, *args, **options):
        teachers = TeacherProfile.objects.select_related('user').all()
        
        self.stdout.write(self.style.WARNING(f'Found {teachers.count()} teachers'))
        
        fixed_count = 0
        for teacher in teachers:
            user = teacher.user
            
            # Check if first_name and last_name are empty
            if not user.first_name and not user.last_name:
                # Try to split username into first and last name
                username_parts = user.username.split('_')
                
                if len(username_parts) >= 2:
                    user.first_name = username_parts[0].capitalize()
                    user.last_name = ' '.join(username_parts[1:]).capitalize()
                else:
                    # If username can't be split, use it as first name
                    user.first_name = user.username.capitalize()
                    user.last_name = 'Teacher'
                
                user.save()
                fixed_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Fixed: {teacher.employee_id} - {user.username} -> '
                        f'{user.first_name} {user.last_name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'OK: {teacher.employee_id} - {user.get_full_name()}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Fixed {fixed_count} teacher names.'
            )
        )
