from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.db import models
from .models import FeeStructure, StudentFee, FeePayment, FeeWaiver
from accounts.models import User, StudentProfile


class FeePaymentForm(forms.ModelForm):
    """Custom form to filter collected_by field to show only admin users"""
    class Meta:
        model = FeePayment
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter collected_by to show only admin users
        if 'collected_by' in self.fields:
            self.fields['collected_by'].queryset = User.objects.filter(user_type='admin')


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('class_assigned', 'academic_year', 'frequency', 'total_fee', 'due_date', 'is_active')
    list_filter = ('academic_year', 'frequency', 'is_active', 'class_assigned__course')
    search_fields = ('class_assigned__name', 'description')
    readonly_fields = ('total_fee', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Class Information', {
            'fields': ('class_assigned', 'academic_year', 'frequency', 'due_date')
        }),
        ('Fee Components', {
            'fields': ('tuition_fee', 'library_fee', 'lab_fee', 'sports_fee', 'transport_fee', 'other_fee', 'total_fee')
        }),
        ('Late Fee Settings', {
            'fields': ('late_fee_amount', 'late_fee_applicable_after_days')
        }),
        ('Additional Information', {
            'fields': ('description', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    def total_fee(self, obj):
        if obj.pk:  # Only calculate if object is saved
            return f"${obj.total_fee:,.2f}"
        return "-"
    total_fee.short_description = 'Total Fee'


class FeePaymentInline(admin.TabularInline):
    model = FeePayment
    form = FeePaymentForm
    extra = 0
    readonly_fields = ('receipt_number', 'created_at')
    fields = ('amount', 'payment_method', 'payment_date', 'transaction_id', 'receipt_number', 'collected_by')


class FeeWaiverInline(admin.TabularInline):
    model = FeeWaiver
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('waiver_type', 'amount', 'percentage', 'reason', 'approved_by', 'is_active')


class StudentFeeForm(forms.ModelForm):
    """Custom form to display student names in dropdown"""
    class Meta:
        model = StudentFee
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize student field to show full name and student ID
        if 'student' in self.fields:
            students = StudentProfile.objects.select_related('user').order_by('user__first_name', 'user__last_name')
            # Create choices with student name (or username if no name) and ID
            def get_student_label(obj):
                full_name = obj.user.get_full_name()
                display_name = full_name if full_name else obj.user.username
                return f"{display_name} ({obj.student_id})"
            
            self.fields['student'].label_from_instance = get_student_label


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    form = StudentFeeForm
    list_display = ('student_name', 'student_id', 'fee_structure', 'amount_due_display', 'amount_paid_display', 
                    'balance_display', 'payment_status_badge', 'due_date')
    list_filter = ('payment_status', 'fee_structure__academic_year', 'fee_structure__frequency', 
                   'fee_structure__class_assigned__course')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__student_id')
    readonly_fields = ('balance_amount', 'is_paid', 'is_overdue', 'created_at', 'updated_at')
    inlines = [FeePaymentInline, FeeWaiverInline]
    list_select_related = ('student', 'student__user', 'fee_structure', 'fee_structure__class_assigned', 'fee_structure__academic_year')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize the student dropdown to show name and ID"""
        if db_field.name == "student":
            kwargs["queryset"] = StudentProfile.objects.select_related('user').order_by('user__first_name', 'user__last_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'fee_structure')
        }),
        ('Fee Details', {
            'fields': ('amount_due', 'amount_paid', 'late_fee_charged', 'discount_amount', 'balance_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_method', 'payment_date', 'transaction_id')
        }),
        ('Status', {
            'fields': ('is_paid', 'is_overdue', 'remarks')
        }),
        ('Notifications', {
            'fields': ('is_notified', 'notification_sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'send_payment_reminder']
    
    def student_name(self, obj):
        if obj.student and obj.student.user:
            full_name = obj.student.user.get_full_name()
            if full_name:
                return full_name
            return obj.student.user.username
        return "N/A"
    student_name.short_description = 'Student Name'
    student_name.admin_order_field = 'student__user__first_name'
    
    def student_id(self, obj):
        if obj.student:
            return obj.student.student_id
        return "N/A"
    student_id.short_description = 'Student ID'
    student_id.admin_order_field = 'student__student_id'
    
    def amount_due_display(self, obj):
        if not obj.pk:
            return "-"
        return f"${obj.amount_due:,.2f}"
    amount_due_display.short_description = 'Amount Due'
    
    def amount_paid_display(self, obj):
        if not obj.pk:
            return "-"
        return f"${obj.amount_paid:,.2f}"
    amount_paid_display.short_description = 'Amount Paid'
    
    def balance_display(self, obj):
        if not obj.pk:
            return "-"
        balance = obj.balance_amount
        color = 'green' if balance <= 0 else 'red'
        return format_html('<span style="color: {};">${}</span>', color, f"{balance:,.2f}")
    balance_display.short_description = 'Balance'
    
    def payment_status_badge(self, obj):
        colors = {
            'paid': 'green',
            'partial': 'orange',
            'pending': 'gray',
            'overdue': 'red',
            'waived': 'blue'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Status'
    
    def due_date(self, obj):
        return obj.fee_structure.due_date
    due_date.short_description = 'Due Date'
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(payment_status='paid', amount_paid=models.F('amount_due'))
        self.message_user(request, f'{updated} fee records marked as paid.')
    mark_as_paid.short_description = 'Mark selected fees as paid'
    
    def send_payment_reminder(self, request, queryset):
        # Implement notification logic here
        count = queryset.filter(payment_status__in=['pending', 'overdue']).count()
        self.message_user(request, f'Payment reminders sent to {count} students.')
    send_payment_reminder.short_description = 'Send payment reminder'


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    form = FeePaymentForm
    list_display = ('receipt_number', 'student_name', 'amount', 'payment_method', 'payment_date', 'collected_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('receipt_number', 'transaction_id', 'student_fee__student__user__first_name', 
                     'student_fee__student__user__last_name')
    readonly_fields = ('receipt_number', 'created_at')
    
    def student_name(self, obj):
        return obj.student_fee.student.user.get_full_name()
    student_name.short_description = 'Student'


@admin.register(FeeWaiver)
class FeeWaiverAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'waiver_type', 'amount', 'percentage', 'approved_by', 'approved_date', 'is_active')
    list_filter = ('waiver_type', 'is_active', 'approved_date')
    search_fields = ('student_fee__student__user__first_name', 'student_fee__student__user__last_name', 'reason')
    
    def student_name(self, obj):
        return obj.student_fee.student.user.get_full_name()
    student_name.short_description = 'Student'
