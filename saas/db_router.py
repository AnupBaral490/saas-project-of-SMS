"""
Database routing for multi-tenant architecture.
Routes all database operations to the correct tenant database based on organization.
"""
import threading
from django.conf import settings

# Thread-local storage for the current database/tenant
_thread_locals = threading.local()


# Apps that must always use the control-plane database.
SHARED_APP_LABELS = {
    'admin',
    'auth',
    'contenttypes',
    'sessions',
    'sites',
    'saas',
}

# Shared apps that should be tenant-scoped when a tenant DB is active.
TENANT_SHARED_APP_LABELS = {
    'admin',
    'contenttypes',
    'auth',
}

# Shared apps that also need schema on tenant DBs for FK constraints.
SHARED_MIGRATION_APP_LABELS = {
    'saas',
    'admin',
    'contenttypes',
    'auth',
}


def set_tenant_db(organization_id=None):
    """Set the active tenant database for this thread"""
    if organization_id:
        if isinstance(organization_id, str) and organization_id.startswith('tenant_'):
            _thread_locals.tenant_db = organization_id
        else:
            _thread_locals.tenant_db = f'tenant_{organization_id}'
    else:
        _thread_locals.tenant_db = 'default'


def set_tenant_db_alias(db_alias):
    """Set the active tenant database alias directly."""
    if db_alias:
        _thread_locals.tenant_db = db_alias
    else:
        _thread_locals.tenant_db = 'default'


def get_tenant_db():
    """Get the active tenant database for this thread"""
    return getattr(_thread_locals, 'tenant_db', 'default')


def clear_tenant_db():
    """Clear the active tenant database"""
    if hasattr(_thread_locals, 'tenant_db'):
        delattr(_thread_locals, 'tenant_db')


class TenantDatabaseRouter:
    """
    A router to control all database operations on models registered
    with the tenant database.
    
    Sessions and auth-related tables always use the default database.
    """

    def db_for_read(self, model, **hints):
        """
        Route read operations to the tenant database, except for specific apps.
        """
        # Keep control-plane models in the shared database.
        if model._meta.app_label in SHARED_APP_LABELS:
            if model._meta.app_label in TENANT_SHARED_APP_LABELS and get_tenant_db().startswith('tenant_'):
                return get_tenant_db()
            return 'default'
        
        return get_tenant_db()

    def db_for_write(self, model, **hints):
        """
        Route write operations to the tenant database, except for specific apps.
        """
        # Keep control-plane models in the shared database.
        if model._meta.app_label in SHARED_APP_LABELS:
            if model._meta.app_label in TENANT_SHARED_APP_LABELS and get_tenant_db().startswith('tenant_'):
                return get_tenant_db()
            return 'default'
        
        return get_tenant_db()

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects in the same database.
        """
        db1 = getattr(obj1._state, 'db', None)
        db2 = getattr(obj2._state, 'db', None)

        if db1 and db2 and db1 == db2:
            return True

        # Allow cross-db relations when a shared (control-plane) model is involved.
        if obj1._meta.app_label in SHARED_APP_LABELS or obj2._meta.app_label in SHARED_APP_LABELS:
            return True

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control which databases migrations are applied to.
        Allow migrations on all configured databases.
        """
        if db not in settings.DATABASES:
            return None

        # Shared apps only migrate on control-plane database.
        if app_label in SHARED_APP_LABELS:
            if app_label in SHARED_MIGRATION_APP_LABELS and db.startswith('tenant_'):
                return True
            return db == 'default'

        # Tenant data apps can migrate on default (legacy compatibility)
        # and all tenant_* databases.
        if db == 'default' or db.startswith('tenant_'):
            return True
        
        return None  # Default behavior for other databases
