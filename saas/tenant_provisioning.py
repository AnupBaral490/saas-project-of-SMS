"""
Utilities for provisioning and maintaining tenant databases.
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command


def add_tenant_database_to_config(organization_id, organization_slug):
    """Register a tenant database alias in Django settings at runtime."""
    db_name = f"tenant_{organization_id}"

    if db_name not in settings.DATABASES:
        base_config = settings.DATABASES.get("default", {}).copy()
        if not base_config:
            base_config = {
                "ENGINE": "django.db.backends.sqlite3",
            }
        base_config["NAME"] = settings.BASE_DIR / "tenant_databases" / f"db_{organization_slug}.sqlite3"
        base_config.setdefault("TIME_ZONE", settings.TIME_ZONE)
        settings.DATABASES[db_name] = base_config

    return db_name


def ensure_tenant_database(
    organization,
    run_migrations=True,
    migrate_if_exists=False,
    verbosity=0,
):
    """
    Ensure tenant DB config and file exist for an organization.

    Returns a tuple: (db_alias, db_path, created_new_db)
    """
    db_alias = add_tenant_database_to_config(organization.id, organization.slug)
    db_path = Path(settings.DATABASES[db_alias]["NAME"])

    db_path.parent.mkdir(parents=True, exist_ok=True)
    created_new_db = not db_path.exists()

    # Touch the database file so migrations can run reliably.
    db_path.touch(exist_ok=True)

    if run_migrations and (created_new_db or migrate_if_exists):
        call_command("migrate", database=db_alias, interactive=False, verbosity=verbosity)

    return db_alias, db_path, created_new_db


def ensure_tenant_admin_from_user(organization, source_user):
    """
    Mirror a control-plane admin user into tenant database.

    We intentionally store organization_id as NULL in tenant DB user rows
    to avoid cross-database foreign key dependencies.
    """
    from accounts.models import User

    db_alias = add_tenant_database_to_config(organization.id, organization.slug)

    tenant_user, created = User.objects.using(db_alias).get_or_create(
        username=source_user.username,
        defaults={
            "email": source_user.email,
            "first_name": source_user.first_name,
            "last_name": source_user.last_name,
            "user_type": "admin",
            "is_staff": True,
            "is_superuser": False,
            "is_active": source_user.is_active,
            "organization_id": None,
            "password": source_user.password,
        },
    )

    if not created:
        tenant_user.email = source_user.email
        tenant_user.first_name = source_user.first_name
        tenant_user.last_name = source_user.last_name
        tenant_user.user_type = "admin"
        tenant_user.is_staff = True
        tenant_user.is_superuser = False
        tenant_user.is_active = source_user.is_active
        tenant_user.organization_id = None
        tenant_user.password = source_user.password
        tenant_user.save(
            using=db_alias,
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "user_type",
                "is_staff",
                "is_superuser",
                "is_active",
                "organization",
                "password",
            ],
        )

    return tenant_user, created


def create_or_update_tenant_admin(organization, username, email, raw_password):
    """Create or update a default tenant admin user in tenant DB only."""
    from accounts.models import User

    db_alias = add_tenant_database_to_config(organization.id, organization.slug)

    tenant_user, created = User.objects.using(db_alias).get_or_create(
        username=username,
        defaults={
            "email": email,
            "user_type": "admin",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "organization_id": None,
        },
    )

    tenant_user.email = email
    tenant_user.user_type = "admin"
    tenant_user.is_staff = True
    tenant_user.is_superuser = True
    tenant_user.is_active = True
    tenant_user.organization_id = None
    tenant_user.set_password(raw_password)
    tenant_user.save(using=db_alias)

    return tenant_user, created
