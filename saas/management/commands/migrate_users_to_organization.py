from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from saas.models import Organization

User = get_user_model()


class Command(BaseCommand):
    help = 'Migrate existing users without organization to the default organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-slug',
            type=str,
            default='sos-herman-gmeiner-school',
            help='Slug of organization to assign users to'
        )

    def handle(self, *args, **options):
        org_slug = options['org_slug']

        # Get organization
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            raise CommandError(f'Organization with slug "{org_slug}" does not exist')

        # Find users without organization
        orphan_users = User.objects.filter(organization__isnull=True)
        orphan_count = orphan_users.count()

        if orphan_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ All users already have organization set')
            )
            return

        self.stdout.write(
            f'\nFound {orphan_count} users without organization\n'
        )
        self.stdout.write(f'Assigning to organization: {org.name}\n')

        # Show sample of users being migrated
        sample_users = orphan_users[:10]
        for user in sample_users:
            self.stdout.write(f'  ├─ {user.username} ({user.user_type})')

        if orphan_count > 10:
            self.stdout.write(f'  ├─ ... and {orphan_count - 10} more')

        # Ask for confirmation
        self.stdout.write(
            self.style.WARNING(
                f'\nThis will assign {orphan_count} users to "{org.name}"'
            )
        )
        confirm = input('\nContinue? (yes/no): ').strip().lower()

        if confirm != 'yes':
            self.stdout.write(self.style.ERROR('Cancelled'))
            return

        # Update users
        updated = orphan_users.update(organization=org)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully migrated {updated} users to "{org.name}"\n'
            )
        )

        # Show summary
        with_org = User.objects.filter(organization=org).count()
        self.stdout.write(f'Organization "{org.name}" now has {with_org} users\n')

        # Verify
        still_orphan = User.objects.filter(organization__isnull=True)
        if still_orphan.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'⚠ {still_orphan.count()} users still have no organization'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ All users now have organization set!')
            )
