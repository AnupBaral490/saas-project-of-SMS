"""
Public SaaS signup and onboarding views
"""
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from saas.models import Organization, OrganizationDomain, SubscriptionPlan, Subscription
from saas.billing_utils import BillingService
from saas.tenant_provisioning import ensure_tenant_database, ensure_tenant_admin_from_user
from accounts.models import StudentProfile, TeacherProfile
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class OrganizationSignUpForm(forms.Form):
    """Form for creating new organization"""
    org_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Organization Name (e.g., Sos Herman Gmeiner School)'
        })
    )
    subdomain = forms.SlugField(
        max_length=63,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'subdomain (auto-generated)',
            'readonly': 'readonly'
        }),
        help_text='Auto-generated from your organization name. Must be unique.'
    )
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contact Email'
        })
    )
    contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone (optional)'
        })
    )
    
    def clean_org_name(self):
        """Auto-generate subdomain from org name"""
        org_name = self.cleaned_data.get('org_name')
        if org_name:
            # Auto-generate slug
            auto_slug = slugify(org_name)
            # Check if exists
            if Organization.objects.filter(slug=auto_slug).exists() or \
               OrganizationDomain.objects.filter(domain=auto_slug).exists():
                raise forms.ValidationError(
                    f'Organization name "{org_name}" is already taken. Please choose another name.'
                )
        return org_name
    
    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain') or slugify(self.cleaned_data.get('org_name', ''))
        
        if not subdomain:
            raise forms.ValidationError('Organization name is required')
        
        if OrganizationDomain.objects.filter(domain=subdomain).exists():
            raise forms.ValidationError(f'Subdomain "{subdomain}" is already taken. Please use a different name.')
        if Organization.objects.filter(subdomain=subdomain).exists():
            raise forms.ValidationError(f'Subdomain "{subdomain}" is already taken. Please use a different name.')
        return subdomain


class AdminUserSignUpForm(forms.Form):
    """Form for creating admin user"""
    full_name = forms.CharField(
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full Name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password_confirm = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match')
        
        if password and len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters')
        
        return cleaned_data


class PlanSelectionForm(forms.Form):
    """Form for selecting subscription plan"""
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        widget=forms.RadioSelect,
        required=True,
    )


@transaction.atomic
def signup_step1_organization(request):
    """Step 1: Create organization"""
    if request.user.is_authenticated and hasattr(request.user, 'organization'):
        return redirect('saas:dashboard')
    
    if request.method == 'POST':
        form = OrganizationSignUpForm(request.POST)
        if form.is_valid():
            org_name = form.cleaned_data['org_name']
            # Auto-generate slug/subdomain from name if not provided
            subdomain = form.cleaned_data.get('subdomain') or slugify(org_name)
            
            # Create organization
            org = Organization.objects.create(
                name=org_name,
                slug=slugify(org_name),
                subdomain=subdomain,
                contact_email=form.cleaned_data['contact_email'],
                phone=form.cleaned_data['contact_phone'],
            )
            
            # Create domain
            OrganizationDomain.objects.create(
                organization=org,
                domain=f"{subdomain}.localhost:8000",  # Development
                is_primary=True,
            )
            
            # Store in session
            request.session['signup_org_id'] = org.id
            
            logger.info(f"New organization created: {org.name} (subdomain: {subdomain})")
            
            return redirect('saas:signup_step2_admin')
    else:
        form = OrganizationSignUpForm()
    
    return render(request, 'saas/signup_step1.html', {'form': form})


@transaction.atomic
def signup_step2_admin(request):
    """Step 2: Create admin user"""
    org_id = request.session.get('signup_org_id')
    if not org_id:
        return redirect('saas:signup_step1_organization')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        form = AdminUserSignUpForm(request.POST)
        if form.is_valid():
            # Create admin user
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['full_name'].split()[0],
                last_name=' '.join(form.cleaned_data['full_name'].split()[1:]),
                organization=org,
                user_type='admin',
                is_staff=True,
                is_superuser=False,  # Not Django superuser
            )
            
            # Admin profile can be created later in admin panel
            # Store in session
            request.session['signup_user_id'] = user.id
            
            logger.info(f"Admin user created: {user.email}")
            
            return redirect('saas:signup_step3_plan')
    else:
        form = AdminUserSignUpForm()
    
    return render(request, 'saas/signup_step2.html', {
        'form': form,
        'organization': org
    })


def signup_step3_plan(request):
    """Step 3: Select subscription plan"""
    org_id = request.session.get('signup_org_id')
    user_id = request.session.get('signup_user_id')
    
    if not org_id or not user_id:
        return redirect('saas:signup_step1_organization')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        form = PlanSelectionForm(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            
            # Start trial or subscription
            if plan.price == 0:
                # Free plan
                Subscription.objects.create(
                    organization=org,
                    plan=plan,
                    status='active',
                    starts_at=timezone.now(),
                )
                request.session['signup_plan_selected'] = plan.id
                return redirect('saas:signup_complete')
            else:
                # Store plan and redirect to payment
                request.session['signup_plan_selected'] = plan.id
                return redirect('saas:signup_step4_payment')
    else:
        form = PlanSelectionForm()
    
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    return render(request, 'saas/signup_step3.html', {
        'form': form,
        'plans': plans,
        'organization': org
    })


def signup_step4_payment(request):
    """Step 4: Payment method"""
    from saas.billing_utils import StripePaymentProcessor
    from django.conf import settings
    
    org_id = request.session.get('signup_org_id')
    user_id = request.session.get('signup_user_id')
    plan_id = request.session.get('signup_plan_selected')
    
    if not all([org_id, user_id, plan_id]):
        return redirect('saas:signup_step1_organization')
    
    org = get_object_or_404(Organization, id=org_id)
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    if request.method == 'POST':
        # In production, use Stripe.js to tokenize card
        # For now, we'll assume a token from Stripe.js
        stripe_token = request.POST.get('stripeToken')
        
        if stripe_token:
            try:
                # Create subscription with Stripe
                stripe_sub, sub_model = StripePaymentProcessor.create_subscription(org, plan)
                
                if sub_model:
                    request.session['signup_subscription_id'] = sub_model.id
                    return redirect('saas:signup_complete')
                else:
                    messages.error(request, 'Failed to create subscription. Please try again.')
            except Exception as e:
                logger.error(f"Payment error: {str(e)}")
                messages.error(request, f'Payment error: {str(e)}')
    
    return render(request, 'saas/signup_step4.html', {
        'organization': org,
        'plan': plan,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    })


def signup_complete(request):
    """Signup complete - provision account"""
    org_id = request.session.get('signup_org_id')
    user_id = request.session.get('signup_user_id')
    
    if not org_id or not user_id:
        return redirect('saas:signup_step1_organization')
    
    org = get_object_or_404(Organization, id=org_id)
    user = get_object_or_404(User, id=user_id)

    # Ensure tenant DB is ready before first login.
    try:
        ensure_tenant_database(org, run_migrations=True, verbosity=0)
        ensure_tenant_admin_from_user(org, user)
    except Exception as exc:
        logger.exception("Failed provisioning tenant DB for organization %s", org.id)
        messages.error(
            request,
            'Your organization was created, but tenant setup is incomplete. Please contact support.',
        )
        return redirect('saas:signup_step1_organization')
    
    # Clean up session
    for key in ['signup_org_id', 'signup_user_id', 'signup_plan_selected', 'signup_subscription_id']:
        request.session.pop(key, None)
    
    # Log in user
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    
    return render(request, 'saas/signup_complete.html', {
        'organization': org,
        'user': user
    })


def pricing(request):
    """Public pricing page"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    return render(request, 'saas/pricing.html', {
        'plans': plans
    })


def features(request):
    """Public features page"""
    return render(request, 'saas/features.html')


def api_check_subdomain(request):
    """API endpoint to check subdomain availability"""
    subdomain = request.GET.get('subdomain', '').strip().lower()
    
    if not subdomain or len(subdomain) < 3:
        return JsonResponse({'available': False, 'message': 'Subdomain too short'})
    
    taken = (
        OrganizationDomain.objects.filter(domain=subdomain).exists() or
        Organization.objects.filter(subdomain=subdomain).exists()
    )
    
    return JsonResponse({
        'available': not taken,
        'message': 'Subdomain taken' if taken else 'Available'
    })


@require_http_methods(['GET'])
def dashboard(request):
    """Tenant dashboard"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    org = request.user.organization
    if not org:
        return redirect('saas:signup_step1_organization')
    
    # Get subscription info
    sub = org.current_subscription
    recent_invoices = org.invoices.all()[:5] if sub else []
    
    context = {
        'organization': org,
        'subscription': sub,
        'recent_invoices': recent_invoices,
        'user_count': org.user_count,
        'student_count': org.student_count,
        'teacher_count': org.teacher_count,
    }
    
    return render(request, 'saas/dashboard.html', context)


@require_http_methods(['GET'])
def invoice_detail(request, invoice_id):
    """View invoice"""
    from django.shortcuts import get_object_or_404
    from saas.models import Invoice
    
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    invoice = get_object_or_404(Invoice, id=invoice_id, organization=request.user.organization)
    
    return render(request, 'saas/invoice_detail.html', {
        'invoice': invoice
    })
