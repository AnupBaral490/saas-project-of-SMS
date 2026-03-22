"""
Management command to provision a new tenant database for an organization.

Usage:
    python manage.py provision_tenant_database <organization_id> [--migrate] [--create-admin]
    python manage.py provision_tenant_database 1 --migrate --create-admin
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
from saas.models import Organization
from saas.tenant_provisioning import (
    create_or_update_tenant_admin,
    ensure_tenant_database,
    ensure_tenant_organization,
)


class Command(BaseCommand):
    help = "Provision a new database for a tenant organization"

    def add_arguments(self, parser):
        parser.add_argument(
            'organization_id',
            type=int,
            help='The ID of the organization to provision a database for'
        )
        parser.add_argument(
            '--migrate',
            action='store_true',
            help='Run migrations on the new tenant database'
        )
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='Create an initial admin user for the tenant'
        )

    def handle(self, *args, **options):
        organization_id = options['organization_id']
        should_migrate = options['migrate']
        create_admin = options['create_admin']

        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise CommandError(f'Organization with ID {organization_id} does not exist')

        self.stdout.write(f'Provisioning tenant database for: {organization.name}')

        # Create DB config/file and optionally migrate it.
        try:
            db_name, db_file, created_new = ensure_tenant_database(
                organization,
                run_migrations=should_migrate,
                migrate_if_exists=should_migrate,
                verbosity=2 if should_migrate else 0,
            )
        except Exception as e:
            raise CommandError(f'Failed to provision tenant database: {str(e)}')

        ensure_tenant_organization(organization, db_alias=db_name)

        self.stdout.write(self.style.SUCCESS(f'✓ Added database configuration: {db_name}'))
        self.stdout.write(self.style.SUCCESS('✓ Created tenant_databases directory'))
        self.stdout.write(f'Database file location: {db_file}')

        if should_migrate:
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))

        # Create an initial admin user if requested
        if create_admin:
            self.stdout.write('Creating initial admin user...')

            try:
                # Ensure saas tables exist for FK constraints.
                connection = connections[db_name]
                saas_tables = connection.introspection.table_names()
                if 'saas_organization' not in saas_tables:
                    call_command(
                        'migrate',
                        'saas',
                        'zero',
                        database=db_name,
                        verbosity=1,
                        interactive=False,
                        fake=True,
                    )
                    call_command(
                        'migrate',
                        'saas',
                        database=db_name,
                        verbosity=1,
                        interactive=False,
                    )

                admin_username = f'admin_{organization.slug}'
                admin_email = f'admin@{organization.slug}.local'
                admin_password = 'AdminPassword123!'

                _, created = create_or_update_tenant_admin(
                    organization,
                    username=admin_username,
                    email=admin_email,
                    raw_password=admin_password,
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Created admin user: {admin_username}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'✓ Updated admin user: {admin_username}'))
                self.stdout.write(f'  Password: {admin_password}')
                self.stdout.write(f'  Email: {admin_email}')
            except Exception as e:
                raise CommandError(f'Failed to create admin user: {str(e)}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Tenant Database Provisioning Complete!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'Organization: {organization.name}')
        self.stdout.write(f'Database: {db_name}')
        self.stdout.write(f'Location: {db_file}')
        
        # Show access information
        self.stdout.write(self.style.SUCCESS('\nAccess Information:'))
        self.stdout.write(f'Domain: {organization.subdomain}.local or use registered domains')
        if organization.domains.exists():
            for domain in organization.domains.all():
                self.stdout.write(f'  - {domain.domain}')

        self.stdout.write(self.style.SUCCESS('\nNext Steps:'))
        self.stdout.write('1. Configure organization domains in Django admin')
        self.stdout.write('2. Login to the tenant dashboard using the admin credentials')
        self.stdout.write('3. Import or create student/teacher data as needed')
