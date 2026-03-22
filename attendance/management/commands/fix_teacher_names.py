from django.core.management.base import BaseCommand
from accounts.models import TeacherProfile

class Command(BaseCommand):
    help = 'Fix teacher names that are empty'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Fixing teacher names...'))
        
        teachers = TeacherProfile.objects.all()
        
        for teacher in teachers:
            user = teacher.user
            
            # If first_name or last_name is empty, set them based on username
            if not user.first_name and not user.last_name:
                # Use username as first name, capitalize it
                user.first_name = user.username.capitalize()
                user.last_name = "Teacher"
                user.save()
                
                self.stdout.write(f'Fixed name for {user.username}: {user.get_full_name()}')
            else:
                self.stdout.write(f'Name OK for {user.username}: {user.get_full_name()}')
        
        self.stdout.write(self.style.SUCCESS('Teacher names fixed!'))