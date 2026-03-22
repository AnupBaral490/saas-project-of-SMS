from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from saas.models import Organization, OrganizationDomain, Subscription, SubscriptionPlan


class Command(BaseCommand):
    help = 'Create or update a tenant organization, domain, plan, and subscription for local SaaS bootstrapping.'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Organization name')
        parser.add_argument('--slug', required=True, help='Organization slug')
        parser.add_argument('--subdomain', help='Subdomain used for host-based resolution')
        parser.add_argument('--domain', help='Full domain name used for host-based resolution')
        parser.add_argument('--plan-code', default='starter', help='Subscription plan code')
        parser.add_argument('--plan-name', default='Starter', help='Subscription plan name')
        parser.add_argument('--price', default='0.00', help='Plan price')
        parser.add_argument('--billing-cycle', choices=['monthly', 'yearly'], default='monthly')
        parser.add_argument('--status', choices=['trial', 'active', 'past_due', 'suspended', 'canceled'], default='trial')
        parser.add_argument('--trial-days', type=int, default=14)
        parser.add_argument('--admin-username', help='Existing username to attach to the organization')

    def handle(self, *args, **options):
        organization, _ = Organization.objects.update_or_create(
            slug=options['slug'],
            defaults={
                'name': options['name'],
                'subdomain': options.get('subdomain') or options['slug'],
            },
        )

        domain = options.get('domain')
        if domain:
            OrganizationDomain.objects.update_or_create(
                domain=domain,
                defaults={
                    'organization': organization,
                    'is_primary': True,
                    'is_active': True,
                },
            )

        plan, _ = SubscriptionPlan.objects.update_or_create(
            code=options['plan_code'],
            defaults={
                'name': options['plan_name'],
                'price': options['price'],
                'billing_cycle': options['billing_cycle'],
                'trial_days': options['trial_days'],
                'is_active': True,
            },
        )

        now = timezone.now()
        trial_ends_at = now + timedelta(days=options['trial_days']) if options['status'] == 'trial' else None
        current_period_end = now + timedelta(days=30 if options['billing_cycle'] == 'monthly' else 365)

        Subscription.objects.create(
            organization=organization,
            plan=plan,
            status=options['status'],
            starts_at=now,
            current_period_end=current_period_end,
            trial_ends_at=trial_ends_at,
        )

        admin_username = options.get('admin_username')
        if admin_username:
            try:
                user = User.objects.get(username=admin_username)
            except User.DoesNotExist as exc:
                raise CommandError(f'User "{admin_username}" does not exist.') from exc
            user.organization = organization
            user.save(update_fields=['organization'])

        self.stdout.write(self.style.SUCCESS(f'Organization {organization.slug} is ready.'))
