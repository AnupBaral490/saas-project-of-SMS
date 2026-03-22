from django.conf import settings
from .db_router import get_tenant_db
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import Organization, OrganizationDomain


LOCAL_HOSTS = {'127.0.0.1', 'localhost'}


def get_host_without_port(request):
    host = request.get_host().split(':', 1)[0].strip().lower()
    return host


def get_request_organization(request):
    return getattr(request, 'organization', None)


def resolve_organization_from_request(request):
    host = get_host_without_port(request)

    organization = Organization.objects.filter(
        domains__domain__iexact=host,
        domains__is_active=True,
        is_active=True,
    ).distinct().first()
    if organization:
        return organization

    if host not in LOCAL_HOSTS:
        subdomain = host.split('.')[0]
        organization = Organization.objects.filter(subdomain=subdomain, is_active=True).first()
        if organization:
            return organization

    if settings.DEBUG and host in LOCAL_HOSTS:
        active_organizations = Organization.objects.filter(is_active=True).order_by('created_at')
        if active_organizations.count() == 1:
            return active_organizations.first()

    return None


def get_active_subscription(organization):
    if not organization:
        return None
    return organization.subscriptions.select_related('plan').order_by('-created_at').first()


def organization_allows_access(organization):
    subscription = get_active_subscription(organization)
    if subscription is None:
        return True
    return subscription.is_accessible


def user_belongs_to_organization(user, organization):
    if organization is None:
        return True
    if getattr(user, 'is_superuser', False):
        return True
    # In tenant DB, users don't store organization_id.
    if get_tenant_db() != 'default' and getattr(user, 'organization_id', None) is None:
        return True
    return getattr(user, 'organization_id', None) == organization.id


# ============================================================================
# Tenant-Aware View Mixins
# ============================================================================

class TenantRequiredMixin(LoginRequiredMixin):
    """
    Mixin for views that require a tenant (organization) to be present.
    Automatically filters querysets and context data by organization.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user belongs to the organization"""
        organization = get_request_organization(request)
        
        if not organization:
            raise PermissionDenied("No organization available for this request")
        
        # Check if user belongs to this organization (unless superuser)
        if not user_belongs_to_organization(request.user, organization):
            raise PermissionDenied("You do not have access to this organization")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add organization to context"""
        context = super().get_context_data(**kwargs)
        context['organization'] = get_request_organization(self.request)
        return context


class TenantFilteredQuerysetMixin(TenantRequiredMixin):
    """
    Mixin that automatically filters querysets by organization.
    Use this for ListView, DetailView, etc.
    """
    
    def get_queryset(self):
        """Filter queryset by organization"""
        queryset = super().get_queryset()
        organization = get_request_organization(self.request)
        
        # Check if model has organization field
        if hasattr(queryset.model, '_meta'):
            fields = [f.name for f in queryset.model._meta.get_fields()]
            if 'organization' in fields:
                queryset = queryset.filter(organization=organization)
        
        return queryset


class TenantAwareListView(TenantFilteredQuerysetMixin, ListView):
    """List view that automatically filters by organization"""
    pass


class TenantAwareDetailView(TenantFilteredQuerysetMixin, DetailView):
    """Detail view that automatically filters by organization"""
    pass


class TenantAwareCreateView(TenantRequiredMixin, CreateView):
    """Create view that automatically assigns organization to new objects"""
    
    def form_valid(self, form):
        """Assign organization before saving"""
        organization = get_request_organization(self.request)
        if hasattr(form.instance, 'organization_id') and form.instance.organization_id is None:
            form.instance.organization = organization
        return super().form_valid(form)


class TenantAwareUpdateView(TenantFilteredQuerysetMixin, UpdateView):
    """Update view that ensures object belongs to organization"""
    
    def get_queryset(self):
        """Filter by organization"""
        return super().get_queryset()


class TenantAwareDeleteView(TenantFilteredQuerysetMixin, DeleteView):
    """Delete view that ensures object belongs to organization"""
    
    def get_queryset(self):
        """Filter by organization"""
        return super().get_queryset()

