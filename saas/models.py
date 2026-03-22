from decimal import Decimal

from django.db import models
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    subdomain = models.SlugField(unique=True, blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def current_subscription(self):
        return self.subscriptions.order_by('-created_at').first()
    
    @property
    def subscription_status(self):
        sub = self.current_subscription
        return sub.status if sub else 'no_subscription'
    
    @property
    def user_count(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(organization=self).count()
    
    @property
    def student_count(self):
        from accounts.models import StudentProfile
        return StudentProfile.objects.filter(user__organization=self).count()
    
    @property
    def teacher_count(self):
        from accounts.models import TeacherProfile
        return TeacherProfile.objects.filter(user__organization=self).count()
    
    def is_within_limits(self, user_type='student'):
        """Check if organization is within subscription limits"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        sub = self.current_subscription
        if not sub or not sub.is_accessible:
            return False
        
        plan = sub.plan
        if user_type == 'student' and plan.max_students:
            return self.student_count < plan.max_students
        elif user_type == 'teacher' and plan.max_teachers:
            return self.teacher_count < plan.max_teachers
        elif user_type == 'admin' and plan.max_admins:
            admin_count = User.objects.filter(organization=self, is_staff=True).count()
            return admin_count < plan.max_admins
        return True
    
    def has_feature(self, feature_code):
        """Check if subscription includes a feature"""
        sub = self.current_subscription
        if not sub or not sub.is_accessible:
            return False
        return sub.plan.feature_flags.get(feature_code, False)


class OrganizationDomain(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='domains')
    domain = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'domain']

    def __str__(self):
        return f'{self.domain} -> {self.organization.name}'


class SubscriptionPlan(models.Model):
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    trial_days = models.PositiveIntegerField(default=14)
    max_students = models.PositiveIntegerField(blank=True, null=True)
    max_teachers = models.PositiveIntegerField(blank=True, null=True)
    max_admins = models.PositiveIntegerField(blank=True, null=True)
    feature_flags = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price', 'name']

    def __str__(self):
        return f'{self.name} ({self.billing_cycle})'


class Subscription(models.Model):
    STATUS_CHOICES = (
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('suspended', 'Suspended'),
        ('canceled', 'Canceled'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    starts_at = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(blank=True, null=True)
    trial_ends_at = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    external_customer_id = models.CharField(max_length=120, blank=True)
    external_subscription_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organization.name} - {self.plan.name} - {self.status}'

    @property
    def is_accessible(self):
        if self.status in {'active', 'past_due'}:
            return True
        if self.status == 'trial':
            return not self.trial_ended
        return False

    @property
    def trial_ended(self):
        return bool(self.trial_ends_at and timezone.now() > self.trial_ends_at)
    
    def days_remaining_in_trial(self):
        """Returns days remaining in trial period"""
        if self.status != 'trial' or not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)
    
    def days_remaining_in_period(self):
        """Returns days remaining in current billing period"""
        if not self.current_period_end:
            return 0
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)


class PaymentMethod(models.Model):
    METHOD_TYPE_CHOICES = (
        ('card', 'Credit Card'),
        ('bank', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES)
    
    # Card details (encrypted in production)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    card_exp_month = models.PositiveIntegerField(blank=True, null=True)
    card_exp_year = models.PositiveIntegerField(blank=True, null=True)
    
    # External payment processor tokens
    external_payment_method_id = models.CharField(max_length=120, blank=True, unique=True)
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        if self.method_type == 'card':
            return f'{self.card_brand} ****{self.card_last_four}'
        return f'{self.get_method_type_display()}'
    
    def is_expired(self):
        """Check if card is expired"""
        if self.method_type != 'card' or not self.card_exp_month or not self.card_exp_year:
            return False
        today = timezone.now().date()
        return (self.card_exp_year, self.card_exp_month) < (today.year, today.month)


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, related_name='invoices', null=True, blank=True)
    
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    issued_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    billing_period_start = models.DateField(blank=True, null=True)
    billing_period_end = models.DateField(blank=True, null=True)
    
    description = models.TextField(blank=True)
    external_invoice_id = models.CharField(max_length=120, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_at']
        unique_together = ('organization', 'invoice_number')

    def __str__(self):
        return f'INV-{self.invoice_number} - {self.organization.name}'
    
    @property
    def is_overdue(self):
        if self.status == 'paid' or not self.due_date:
            return False
        return timezone.now().date() > self.due_date
    
    def mark_as_paid(self):
        """Mark invoice as paid"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', blank=True, null=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    external_payment_id = models.CharField(max_length=120, blank=True, unique=True)
    external_transaction_id = models.CharField(max_length=120, blank=True)
    
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organization.name} - {self.amount} - {self.status}'


class PaymentEvent(models.Model):
    """Track webhook events from payment processors"""
    EVENT_TYPE_CHOICES = (
        ('charge.succeeded', 'Charge Succeeded'),
        ('charge.failed', 'Charge Failed'),
        ('invoice.paid', 'Invoice Paid'),
        ('invoice.payment_failed', 'Invoice Payment Failed'),
        ('customer.subscription.created', 'Subscription Created'),
        ('customer.subscription.updated', 'Subscription Updated'),
        ('customer.subscription.deleted', 'Subscription Deleted'),
    )

    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    external_event_id = models.CharField(max_length=120, unique=True)
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payment_events', blank=True, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, related_name='payment_events', blank=True, null=True)
    
    data = models.JSONField(default=dict, blank=True)
    is_processed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('event_type', 'external_event_id')

    def __str__(self):
        return f'{self.event_type} - {self.external_event_id}'
