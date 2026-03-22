"""
Management command to link a parent to their children
Usage: python manage.py link_parent_child <parent_username> <child_username1> [child_username2] ...
"""

from django.core.management.base import BaseCommand
from accounts.models import User, ParentProfile, StudentProfile


class Command(BaseCommand):
    help = 'Link a parent to their children by username'

    def add_arguments(self, parser):
        parser.add_argument('parent_username', type=str, help='Username of the parent')
        parser.add_argument('child_usernames', nargs='+', type=str, help='Username(s) of the child/children')

    def handle(self, *args, **options):
        parent_username = options['parent_username']
        child_usernames = options['child_usernames']

        # Get parent user
        try:
            parent_user = User.objects.get(username=parent_username, user_type='parent')
            self.stdout.write(self.style.SUCCESS(f'Found parent: {parent_user.get_full_name() or parent_username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Parent user "{parent_username}" not found or not a parent type'))
            return

        # Get or create parent profile
        try:
            parent_profile = parent_user.parent_profile
        except ParentProfile.DoesNotExist:
            parent_profile = ParentProfile.objects.create(user=parent_user, occupation='')
            self.stdout.write(self.style.WARNING(f'Created parent profile for {parent_username}'))

        # Link each child
        linked_count = 0
        for child_username in child_usernames:
            try:
                child_user = User.objects.get(username=child_username, user_type='student')
                child_profile = child_user.student_profile
                
                # Check if already linked
                if parent_profile.children.filter(id=child_profile.id).exists():
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  {child_user.get_full_name() or child_username} is already linked'
                    ))
                else:
                    parent_profile.children.add(child_profile)
                    linked_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Linked child: {child_user.get_full_name() or child_username} (ID: {child_profile.student_id})'
                    ))
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Student user "{child_username}" not found or not a student type'
                ))
            except StudentProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Student profile not found for "{child_username}"'
                ))

        if linked_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully linked {linked_count} child(ren) to {parent_username}'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'Total children for {parent_username}: {parent_profile.children.count()}'
            ))
        else:
            self.stdout.write(self.style.WARNING('\nNo new children were linked'))

        # Show current children
        self.stdout.write('\nCurrent children for this parent:')
        for child in parent_profile.children.all():
            self.stdout.write(f'  - {child.user.get_full_name() or child.user.username} ({child.student_id})')
