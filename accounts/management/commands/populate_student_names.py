from django.core.management.base import BaseCommand
from accounts.models import User, StudentProfile

class Command(BaseCommand):
    help = 'Populate first_name and last_name for students from their username'

    def handle(self, *args, **kwargs):
        students = User.objects.filter(user_type='student')
        updated_count = 0
        
        for student in students:
            # Skip if already has first_name and last_name
            if student.first_name and student.last_name:
                continue
            
            # Try to split username into first and last name
            username_parts = student.username.split()
            
            if len(username_parts) >= 2:
                student.first_name = username_parts[0].capitalize()
                student.last_name = ' '.join(username_parts[1:]).capitalize()
            elif len(username_parts) == 1:
                # If only one word, use it as first name
                student.first_name = username_parts[0].capitalize()
                student.last_name = ''
            
            student.save()
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated: {student.username} -> {student.first_name} {student.last_name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully updated {updated_count} student names!'
            )
        )
