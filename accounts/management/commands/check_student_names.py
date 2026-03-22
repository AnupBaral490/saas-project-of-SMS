from django.core.management.base import BaseCommand
from accounts.models import User, StudentProfile

class Command(BaseCommand):
    help = 'Check and display student name information'

    def handle(self, *args, **options):
        students = StudentProfile.objects.select_related('user').all()
        
        self.stdout.write(f"Found {students.count()} students:")
        
        for student in students:
            user = student.user
            full_name = user.get_full_name()
            
            self.stdout.write(
                f"Student ID: {student.student_id}, "
                f"Username: {user.username}, "
                f"First Name: '{user.first_name}', "
                f"Last Name: '{user.last_name}', "
                f"Full Name: '{full_name}', "
                f"Email: {user.email}"
            )
            
            # If no first/last name, suggest using username
            if not full_name.strip():
                self.stdout.write(
                    self.style.WARNING(f"  -> No full name for {user.username}, will use username as fallback")
                )
        
        if students.count() == 0:
            self.stdout.write(self.style.WARNING("No students found in the database"))