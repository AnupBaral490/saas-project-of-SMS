from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Organization, OrganizationDomain, Subscription, SubscriptionPlan,
    PaymentMethod, Invoice, Payment, PaymentEvent
)


class OrganizationDomainInline(admin.TabularInline):
    model = OrganizationDomain
    extra = 1
    fields = ('domain', 'is_primary', 'is_active')
    verbose_name = 'Domain'
    verbose_name_plural = 'Domains (for testing)'


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'subdomain', 'subscription_status', 'user_count', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'subdomain', 'contact_email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'user_count', 'student_count', 'teacher_count')
    inlines = [OrganizationDomainInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'subdomain', 'contact_email', 'phone')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Usage', {
            'fields': ('user_count', 'student_count', 'teacher_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrganizationDomain)
class OrganizationDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'organization', 'is_primary', 'is_active')
    search_fields = ('domain', 'organization__name', 'organization__slug')
    list_filter = ('is_primary', 'is_active')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'billing_cycle', 'price', 'trial_days', 'max_students', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('billing_cycle', 'is_active')
    fieldsets = (
        ('Plan Information', {
            'fields': ('code', 'name', 'description')
        }),
        ('Pricing', {
            'fields': ('billing_cycle', 'price', 'trial_days')
        }),
        ('Limits', {
            'fields': ('max_students', 'max_teachers', 'max_admins')
        }),
        ('Features', {
            'fields': ('feature_flags',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization', 'plan', 'status_badge', 'starts_at', 'current_period_end', 'created_at')
    search_fields = ('organization__name', 'plan__name', 'external_customer_id', 'external_subscription_id')
    list_filter = ('status', 'plan__billing_cycle', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'external_customer_id', 'external_subscription_id')
    
    def status_badge(self, obj):
        colors = {
            'trial': '#FFC107',
            'active': '#28A745',
            'past_due': '#DC3545',
            'suspended': '#FFC107',
            'canceled': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('organization', 'method_type', '__str__', 'is_default', 'is_active', 'created_at')
    search_fields = ('organization__name', 'external_payment_method_id')
    list_filter = ('method_type', 'is_default', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'external_payment_method_id')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'organization', 'status_badge', 'amount', 'total_amount', 'issued_at', 'due_date')
    search_fields = ('invoice_number', 'organization__name', 'external_invoice_id')
    list_filter = ('status', 'issued_at', 'due_date')
    readonly_fields = ('created_at', 'updated_at', 'invoice_number')

    def save_model(self, request, obj, form, change):
        if not obj.invoice_number:
            next_number = Invoice.objects.count() + 1
            candidate = f"{next_number:06d}"
            while Invoice.objects.filter(invoice_number=candidate).exists():
                next_number += 1
                candidate = f"{next_number:06d}"
            obj.invoice_number = candidate
        super().save_model(request, obj, form, change)
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6C757D',
            'pending': '#FFC107',
            'paid': '#28A745',
            'failed': '#DC3545',
            'cancelled': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('organization', 'amount', 'status_badge', 'payment_method', 'created_at', 'processed_at')
    search_fields = ('organization__name', 'external_payment_id', 'external_transaction_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'processed_at', 'external_payment_id')
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFC107',
            'processing': '#17A2B8',
            'completed': '#28A745',
            'failed': '#DC3545',
            'refunded': '#6C757D',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'external_event_id', 'organization', 'is_processed', 'created_at', 'processed_at')
    search_fields = ('external_event_id', 'organization__name', 'event_type')
    list_filter = ('event_type', 'is_processed', 'created_at')
    readonly_fields = ('created_at', 'processed_at', 'data', 'event_type', 'external_event_id', 'organization', 'subscription', 'is_processed')
    
    def has_add_permission(self, request):
        """PaymentEvents are created only through webhook processing"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of webhook events for audit trail"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """PaymentEvents are read-only"""
        return True

