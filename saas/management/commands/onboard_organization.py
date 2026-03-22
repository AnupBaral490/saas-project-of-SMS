from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from saas.models import Organization, OrganizationDomain, Subscription, SubscriptionPlan
from saas.tenant_provisioning import ensure_tenant_admin_from_user, ensure_tenant_database


User = get_user_model()


class Command(BaseCommand):
    help = (
        "One-command onboarding for a new organization: "
        "org/domain/subscription + tenant DB + tenant admin mirror."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Organization name")
        parser.add_argument("--slug", required=True, help="Organization slug")
        parser.add_argument("--subdomain", help="Organization subdomain")
        parser.add_argument("--domain", help="Primary domain to map to organization")

        parser.add_argument("--plan-code", default="starter", help="Existing subscription plan code")
        parser.add_argument(
            "--status",
            choices=["trial", "active", "past_due", "suspended", "canceled"],
            default="trial",
            help="Initial subscription status",
        )
        parser.add_argument("--trial-days", type=int, default=14, help="Trial duration in days")

        parser.add_argument("--admin-username", required=True, help="Initial admin username")
        parser.add_argument("--admin-email", required=True, help="Initial admin email")
        parser.add_argument("--admin-password", required=True, help="Initial admin password")

        parser.add_argument(
            "--migrate",
            action="store_true",
            help="Run migrations while provisioning a new tenant database",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        plan_code = options["plan_code"]

        try:
            plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
        except SubscriptionPlan.DoesNotExist as exc:
            raise CommandError(
                f'Active subscription plan "{plan_code}" was not found. '
                "Run `python manage.py init_subscription_plans` first."
            ) from exc

        organization, _ = Organization.objects.update_or_create(
            slug=options["slug"],
            defaults={
                "name": options["name"],
                "subdomain": options.get("subdomain") or options["slug"],
                "is_active": True,
            },
        )

        domain = options.get("domain")
        if domain:
            OrganizationDomain.objects.update_or_create(
                domain=domain,
                defaults={
                    "organization": organization,
                    "is_primary": True,
                    "is_active": True,
                },
            )

        now = timezone.now()
        status = options["status"]
        trial_days = options["trial_days"]
        trial_ends_at = now + timedelta(days=trial_days) if status == "trial" else None
        current_period_end = now + timedelta(days=30 if plan.billing_cycle == "monthly" else 365)

        Subscription.objects.create(
            organization=organization,
            plan=plan,
            status=status,
            starts_at=now,
            current_period_end=current_period_end,
            trial_ends_at=trial_ends_at,
        )

        admin_user, created = User.objects.update_or_create(
            username=options["admin_username"],
            defaults={
                "email": options["admin_email"],
                "organization": organization,
                "user_type": "admin",
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
            },
        )
        admin_user.set_password(options["admin_password"])
        admin_user.save(update_fields=["password"])

        db_alias, db_path, created_new = ensure_tenant_database(
            organization,
            run_migrations=options["migrate"],
            migrate_if_exists=options["migrate"],
            verbosity=1 if options["migrate"] else 0,
        )
        ensure_tenant_admin_from_user(organization, admin_user)

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Organization onboarding complete"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Organization: {organization.name} ({organization.slug})")
        self.stdout.write(f"Subscription plan: {plan.code} [{status}]")
        self.stdout.write(f"Control admin: {admin_user.username} ({'created' if created else 'updated'})")
        self.stdout.write(f"Tenant DB alias: {db_alias}")
        self.stdout.write(f"Tenant DB file: {db_path}")
        self.stdout.write(f"Tenant DB newly created: {created_new}")
        if domain:
            self.stdout.write(f"Domain: {domain}")
