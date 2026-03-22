from .utils import get_active_subscription, resolve_organization_from_request
from .db_router import set_tenant_db, clear_tenant_db
from .tenant_provisioning import add_tenant_database_to_config


class TenantMiddleware:
    """
    Middleware to detect the tenant (organization) from the request
    and set up the appropriate database routing.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # First, check if user is authenticated and has an organization
        organization = None
        if hasattr(request, 'user') and request.user and request.user.is_authenticated and hasattr(request.user, 'organization_id'):
            if request.user.organization_id:
                from .models import Organization
                organization = Organization.objects.filter(
                    id=request.user.organization_id,
                    is_active=True
                ).first()
        
        # If not from user, resolve from request (domain, subdomain, etc)
        if not organization:
            organization = resolve_organization_from_request(request)
        
        request.organization = organization
        request.subscription = get_active_subscription(organization)
        
        # Set the active tenant database for this request
        if organization:
            add_tenant_database_to_config(organization.id, organization.slug)
            set_tenant_db(organization.id)
        else:
            set_tenant_db(None)
        
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clear the tenant database after request completion, including errors.
            clear_tenant_db()
