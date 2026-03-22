from django.core.management.base import BaseCommand
from accounts.models import User, StudentProfile

class Command(BaseCommand):
    help = 'Fix student names by setting first_name from username where missing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        students = StudentProfile.objects.select_related('user').all()
        
        self.stdout.write(f"Checking {students.count()} students...")
        
        updated_count = 0
        
        for student in students:
            user = student.user
            full_name = user.get_full_name()
            
            # If no first/last name, use username as first name
            if not full_name.strip():
                if options['dry_run']:
                    self.stdout.write(
                        f"Would update: {user.username} -> First Name: '{user.username.title()}'"
                    )
                else:
                    # Capitalize the username and set as first name
                    user.first_name = user.username.title()
                    user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated: {user.username} -> First Name: '{user.first_name}'"
                        )
                    )
                
                updated_count += 1
            else:
                self.stdout.write(f"OK: {user.username} already has name: '{full_name}'")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would update {updated_count} students")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Updated {updated_count} students with missing names")
            )