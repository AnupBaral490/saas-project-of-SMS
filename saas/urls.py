"""
SaaS subscription and billing URLs
"""
from django.urls import path
from saas import signup_views, webhook_views, tenant_dashboard_views

app_name = 'saas'

urlpatterns = [
    # Public signup flow
    path('signup/', signup_views.signup_step1_organization, name='signup_step1_organization'),
    path('signup/admin/', signup_views.signup_step2_admin, name='signup_step2_admin'),
    path('signup/plan/', signup_views.signup_step3_plan, name='signup_step3_plan'),
    path('signup/payment/', signup_views.signup_step4_payment, name='signup_step4_payment'),
    path('signup/complete/', signup_views.signup_complete, name='signup_complete'),
    
    # Public pages
    path('pricing/', signup_views.pricing, name='pricing'),
    path('features/', signup_views.features, name='features'),
    
    # Dashboard
    path('dashboard/', signup_views.dashboard, name='dashboard'),
    
    # Tenant-specific views (organization dashboard)
    path('tenant/dashboard/', tenant_dashboard_views.tenant_dashboard, name='tenant_dashboard'),
    path('tenant/settings/', tenant_dashboard_views.tenant_settings, name='tenant_settings'),
    path('tenant/users/', tenant_dashboard_views.tenant_users, name='tenant_users'),
    path('tenant/subscription/', tenant_dashboard_views.tenant_subscription, name='tenant_subscription'),
    path('tenant/organization-switcher/', tenant_dashboard_views.organization_switcher, name='organization_switcher'),
    path('tenant/switch-organization/', tenant_dashboard_views.switch_organization, name='switch_organization'),
    
    # Invoices
    path('invoices/<int:invoice_id>/', signup_views.invoice_detail, name='invoice_detail'),
    
    # Webhooks
    path('webhooks/stripe/', webhook_views.stripe_webhook, name='stripe_webhook'),
    path('webhooks/razorpay/', webhook_views.razorpay_webhook, name='razorpay_webhook'),
    
    # API
    path('api/check-subdomain/', signup_views.api_check_subdomain, name='api_check_subdomain'),
]
