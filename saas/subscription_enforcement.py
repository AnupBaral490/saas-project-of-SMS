"""
Subscription enforcement decorators and utilities
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from saas.utils import get_request_organization
import logging

logger = logging.getLogger(__name__)


def subscription_required(view_func=None, feature=None, user_type=None):
    """
    Decorator to enforce active subscription for a view
    
    Args:
        feature: Check if specific feature is enabled in subscription
        user_type: Check subscription limits (student/teacher/admin)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            organization = get_request_organization(request)
            
            if not organization:
                return HttpResponseForbidden("Organization not found")
            
            # Check if organization has active subscription
            if not organization.current_subscription:
                return redirect(reverse('saas:subscribe'))
            
            sub = organization.current_subscription
            
            # Check if subscription is accessible
            if not sub.is_accessible:
                return HttpResponseForbidden("Subscription inactive or expired")
            
            # Check feature flag if specified
            if feature and not organization.has_feature(feature):
                return HttpResponseForbidden(f"Feature '{feature}' not available in your plan")
            
            # Check user limits if specified
            if user_type and not organization.is_within_limits(user_type):
                return HttpResponseForbidden(
                    f"You have reached the maximum number of {user_type}s for your plan"
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    
    if view_func is not None:
        return decorator(view_func)
    return decorator


def json_subscription_required(view_func=None, feature=None):
    """
    Decorator for API endpoints requiring subscription
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            organization = get_request_organization(request)
            
            if not organization:
                return JsonResponse({
                    'error': 'Organization not found'
                }, status=403)
            
            if not organization.current_subscription:
                return JsonResponse({
                    'error': 'Active subscription required',
                    'code': 'NO_SUBSCRIPTION'
                }, status=403)
            
            sub = organization.current_subscription
            if not sub.is_accessible:
                return JsonResponse({
                    'error': 'Subscription inactive or expired',
                    'code': 'SUBSCRIPTION_INACTIVE'
                }, status=403)
            
            if feature and not organization.has_feature(feature):
                return JsonResponse({
                    'error': f"Feature '{feature}' not available",
                    'code': 'FEATURE_NOT_AVAILABLE'
                }, status=403)
            
            return func(request, *args, **kwargs)
        return wrapper
    
    if view_func is not None:
        return decorator(view_func)
    return decorator


class SubscriptionMiddleware:
    """
    Middleware to enforce subscription limits on user registration
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a user creation request
        if request.path.startswith('/api/users/create') or request.path.startswith('/accounts/register'):
            organization = get_request_organization(request)
            
            if organization and organization.current_subscription:
                user_type = request.POST.get('user_type') or request.GET.get('user_type')
                
                if user_type and not organization.is_within_limits(user_type):
                    request.subscription_limit_exceeded = True
        
        response = self.get_response(request)
        return response


def check_subscription_limits(organization, user_type):
    """
    Utility function to check subscription limits
    
    Returns:
        Tuple: (is_within_limits: bool, remaining_spots: int, message: str)
    """
    if not organization.current_subscription:
        return False, 0, "No active subscription"
    
    sub = organization.current_subscription
    if not sub.is_accessible:
        return False, 0, "Subscription inactive"
    
    plan = sub.plan
    
    if user_type == 'student':
        current = organization.student_count
        limit = plan.max_students
    elif user_type == 'teacher':
        current = organization.teacher_count
        limit = plan.max_teachers
    elif user_type == 'admin':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        current = User.objects.filter(organization=organization, is_staff=True).count()
        limit = plan.max_admins
    else:
        return False, 0, "Invalid user type"
    
    if limit is None:
        return True, float('inf'), "Unlimited"
    
    if current >= limit:
        return False, 0, f"Limit reached ({limit})"
    
    remaining = limit - current
    return True, remaining, f"{remaining} spots available"


def get_subscription_status_info(organization):
    """
    Get detailed subscription status information
    """
    sub = organization.current_subscription
    
    if not sub:
        return {
            'has_subscription': False,
            'status': 'no_subscription',
            'message': 'No active subscription',
            'can_access': False,
        }
    
    info = {
        'has_subscription': True,
        'plan_name': sub.plan.name,
        'status': sub.status,
        'can_access': sub.is_accessible,
        'billing_cycle': sub.plan.billing_cycle,
        'price': float(sub.plan.price),
    }
    
    if sub.status == 'trial':
        info['trial_days_remaining'] = sub.days_remaining_in_trial()
        info['trial_ends'] = sub.trial_ends_at.isoformat() if sub.trial_ends_at else None
    elif sub.status == 'active':
        info['days_remaining'] = sub.days_remaining_in_period()
        info['period_ends'] = sub.current_period_end.isoformat() if sub.current_period_end else None
    
    # Add usage info
    info['usage'] = {
        'students': organization.student_count,
        'max_students': sub.plan.max_students,
        'teachers': organization.teacher_count,
        'max_teachers': sub.plan.max_teachers,
    }
    
    # Add feature flags
    info['features'] = sub.plan.feature_flags or {}
    
    return info
