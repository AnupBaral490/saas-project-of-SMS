from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import AdminProfile
import getpass

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user for the Student Management System'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username')
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        # Get username if not provided
        if not username:
            username = input('Username: ')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'User with username "{username}" already exists!')
            )
            return

        # Get email if not provided
        if not email:
            email = input('Email: ')

        # Get password if not provided
        if not password:
            password = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Confirm password: ')
            
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match!'))
                return

        try:
            # Create admin user
            admin_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='admin',
                is_staff=True,
                is_superuser=True
            )

            # Create admin profile
            AdminProfile.objects.create(
                user=admin_user,
                employee_id=f'ADM{admin_user.id:06d}',
                department='Administration'
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Admin user "{username}" created successfully!\n'
                    f'Employee ID: ADM{admin_user.id:06d}\n'
                    f'You can now login at http://127.0.0.1:8000/accounts/login/'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )