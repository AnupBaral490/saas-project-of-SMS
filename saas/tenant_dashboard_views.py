"""
Tenant-specific dashboard views for each organization.
These views provide organization-specific dashboards with complete data isolation.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from saas.utils import get_request_organization
from saas.db_router import set_tenant_db


@login_required
@require_http_methods(['GET'])
def tenant_dashboard(request):
    """
    Tenant-specific dashboard - shows organization-specific data and statistics.
    Automatically routes to the correct database based on the tenant.
    """
    organization = get_request_organization(request)
    
    if not organization:
        return redirect('accounts:login')
    
    # Verify user belongs to this organization
    if request.user.organization_id != organization.id and not request.user.is_superuser:
        return redirect('accounts:login')
    
    # Get organization-specific statistics
    from accounts.models import User
    from academic.models import Course, StudentEnrollment
    from attendance.models import AttendanceRecord
    from django.db.models import Q
    
    # Get all users for this organization (filter by organization_id in default DB)
    # Users belong to org either via organization_id (admins) or implicit tenant DB
    org_users = User.objects.filter(
        Q(organization_id=organization.id) | Q(organization_id__isnull=True)
    )
    
    stats = {
        'organization': organization,
        'organization_name': organization.name,
        'organization_slug': organization.slug,
        
        # User statistics - filter by organization
        'total_users': org_users.count(),
        'total_students': org_users.filter(user_type='student', organization_id=organization.id).count(),
        'total_teachers': org_users.filter(user_type='teacher', organization_id=organization.id).count(),
        'total_parents': org_users.filter(user_type='parent', organization_id=organization.id).count(),
        'total_admins': org_users.filter(user_type='admin', organization_id=organization.id).count(),
        
        # Academic statistics (from tenant DB)
        'total_courses': Course.objects.all().count() if hasattr(Course, '_meta') else 0,
        'active_enrollments': StudentEnrollment.objects.filter(
            enrollment_status__in=['active', 'ongoing']
        ).count() if hasattr(StudentEnrollment, '_meta') else 0,
        
        # Subscription information
        'subscription': organization.subscriptions.select_related('plan').first(),
        
        # Recent users from this organization only
        'recent_users': org_users.filter(
            user_type__in=['student', 'teacher', 'parent'],
            organization_id=organization.id
        ).order_by('-date_joined')[:10],
        
        # Feature availability
        'features': organization.subscriptions.first().plan.feature_flags if organization.subscriptions.exists() else {}
    }
    
    context = {
        'page_title': f'{organization.name} - Dashboard',
        'tenant': organization,
        **stats
    }
    
    return render(request, 'saas/tenant_dashboard.html', context)


@login_required
@require_http_methods(['GET'])
def tenant_settings(request):
    """
    Tenant settings page - allows organization admins to manage their organization.
    """
    organization = get_request_organization(request)
    
    if not organization:
        return redirect('accounts:login')
    
    # Only allow admins to access settings
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        return redirect('accounts:dashboard')
    
    if request.user.organization_id != organization.id and not request.user.is_superuser:
        return redirect('accounts:login')
    
    set_tenant_db(organization.id)
    
    # Get organization settings
    from accounts.models import User
    admin_users = User.objects.filter(user_type='admin')
    
    context = {
        'page_title': f'{organization.name} - Settings',
        'tenant': organization,
        'organization': organization,
        'admin_users': admin_users,
        'subscription': organization.subscriptions.select_related('plan').first(),
        'domains': organization.domains.all(),
    }
    
    return render(request, 'saas/tenant_settings.html', context)


@login_required
@require_http_methods(['GET'])
def tenant_users(request):
    """
    Tenant users management page - list and filter users within the organization.
    """
    organization = get_request_organization(request)
    
    if not organization:
        return redirect('accounts:login')
    
    # Only allow admins to access user management
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        return redirect('accounts:dashboard')
    
    if request.user.organization_id != organization.id and not request.user.is_superuser:
        return redirect('accounts:login')
    
    set_tenant_db(organization.id)
    
    from accounts.models import User
    
    # Get filter parameter
    user_type_filter = request.GET.get('type', '')
    
    users = User.objects.all()  # Uses tenant database
    if user_type_filter and user_type_filter in ['student', 'teacher', 'parent', 'admin']:
        users = users.filter(user_type=user_type_filter)
    
    users = users.order_by('-date_joined')
    
    context = {
        'page_title': f'{organization.name} - Users',
        'tenant': organization,
        'organization': organization,
        'users': users,
        'user_type_filter': user_type_filter,
        'users_by_type': {
            'students': User.objects.filter(user_type='student').count(),
            'teachers': User.objects.filter(user_type='teacher').count(),
            'parents': User.objects.filter(user_type='parent').count(),
            'admins': User.objects.filter(user_type='admin').count(),
        }
    }
    
    return render(request, 'saas/tenant_users.html', context)


@login_required
@require_http_methods(['GET'])
def tenant_subscription(request):
    """
    Tenant subscription page - shows current subscription and upgrade options.
    """
    organization = get_request_organization(request)
    
    if not organization:
        return redirect('accounts:login')
    
    # Only allow admins to access subscription management
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        return redirect('accounts:dashboard')
    
    if request.user.organization_id != organization.id and not request.user.is_superuser:
        return redirect('accounts:login')
    
    from saas.models import SubscriptionPlan
    
    current_subscription = organization.subscriptions.select_related('plan').first()
    all_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    context = {
        'page_title': f'{organization.name} - Subscription',
        'tenant': organization,
        'organization': organization,
        'current_subscription': current_subscription,
        'current_plan': current_subscription.plan if current_subscription else None,
        'available_plans': all_plans,
        'subscription_active': current_subscription and current_subscription.is_active,
    }
    
    return render(request, 'saas/tenant_subscription.html', context)


@login_required
@require_http_methods(['GET'])
def organization_switcher(request):
    """
    For superusers - allows switching between organizations.
    """
    if not request.user.is_superuser:
        return redirect('accounts:login')
    
    from saas.models import Organization
    
    organizations = Organization.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_title': 'Organization Switcher',
        'organizations': organizations,
    }
    
    return render(request, 'saas/organization_switcher.html', context)


@login_required
@require_http_methods(['POST'])
def switch_organization(request):
    """
    For superusers - switch to a different organization.
    """
    if not request.user.is_superuser:
        return redirect('accounts:login')
    
    organization_id = request.POST.get('organization_id')
    
    if organization_id:
        from saas.models import Organization
        try:
            organization = Organization.objects.get(id=organization_id, is_active=True)
            # Switch to the organization's domain
            if organization.domains.exists():
                domain = organization.domains.first().domain
                return redirect(f'http://{domain}')
            else:
                # Use subdomain
                return redirect(f'http://{organization.subdomain}.local')
        except Organization.DoesNotExist:
            pass
    
    return redirect('saas:organization_switcher')
