"""
Tenant-aware authentication backend for multi-tenant system
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from saas.utils import resolve_organization_from_request
from saas.db_router import set_tenant_db, clear_tenant_db, get_tenant_db, set_tenant_db_alias
from saas.tenant_provisioning import add_tenant_database_to_config
from saas.models import Organization

User = get_user_model()


class TenantAuthBackend(ModelBackend):
    """
    Custom authentication backend that authenticates against the correct tenant database
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user - tries tenant database first, then default
        """
        if username is None or password is None:
            return None
        
        # Get organization for this request
        try:
            organization = resolve_organization_from_request(request)
            if not organization:
                # For localhost, get first active organization
                organization = Organization.objects.filter(is_active=True).first()
        except:
            organization = None
        
        # If we have an organization, try tenant database
        if organization:
            try:
                add_tenant_database_to_config(organization.id, organization.slug)
                previous_db = get_tenant_db()
                set_tenant_db(organization.id)
                # Use the parent class authenticate which respects the database routing
                user = super().authenticate(request, username=username, password=password, **kwargs)
                if user:
                    return user
            except Exception as e:
                pass
            finally:
                # Restore previous tenant context if it existed.
                if 'previous_db' in locals() and previous_db:
                    set_tenant_db_alias(previous_db)
                else:
                    clear_tenant_db()
        
        # Try default database as fallback
        try:
            user = super().authenticate(request, username=username, password=password, **kwargs)
            return user
        except:
            return None
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            db_alias = get_tenant_db()
            if db_alias and db_alias != 'default':
                return User.objects.using(db_alias).get(pk=user_id)
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
