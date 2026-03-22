from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from saas.utils import get_request_organization
from .models import User, StudentProfile, TeacherProfile, ParentProfile, AdminProfile, ParentTeacherMessage

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'organization', 'user_type', 'is_active')
    list_filter = ('organization', 'user_type', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'organization__name', 'organization__slug')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('organization', 'user_type', 'phone_number', 'address', 'date_of_birth', 'profile_picture')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        
        # For non-superusers, make organization readonly
        if not request.user.is_superuser:
            if 'organization' not in readonly:
                readonly.append('organization')
        
        # When editing an existing object, add password change link
        if obj:
            if 'password_change_link' not in readonly:
                readonly.append('password_change_link')
        
        return readonly
    
    def password_change_link(self, obj):
        if obj.pk:
            url = reverse('admin:auth_user_password_change', args=[obj.pk])
            return format_html(
                'Raw passwords are not stored, so there is no way to see this user\'s password, '
                'but you can change the password using <strong><a href="{}">this form</a></strong>.',
                url
            )
        return ""
    password_change_link.short_description = 'Password'
    
    def get_queryset(self, request):
        """Filter users by organization"""
        queryset = super().get_queryset(request)
        
        # Superusers see all users
        if request.user.is_superuser:
            return queryset
        
        # Regular admins see only their organization's users
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(organization=organization)
        
        return queryset
    
    def save_model(self, request, obj, form, change):
        """Automatically set organization when creating users"""
        # Always ensure organization_id is set from request context
        organization = get_request_organization(request)
        
        if not change:  # Creating new object
            # For new objects, always set organization from request
            if organization:
                obj.organization = organization
                obj.organization_id = organization.id  # Explicitly set ID
        
        super().save_model(request, obj, form, change)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'admission_date', 'guardian_name')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id', 'guardian_name')
    list_filter = ('admission_date',)
    
    def get_queryset(self, request):
        """Filter student profiles by organization"""
        queryset = super().get_queryset(request)
        
        if request.user.is_superuser:
            return queryset
        
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(user__organization=organization)
        
        return queryset

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'specialization', 'experience_years')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id', 'specialization')
    list_filter = ('joining_date', 'experience_years')
    
    def get_queryset(self, request):
        """Filter teacher profiles by organization"""
        queryset = super().get_queryset(request)
        
        if request.user.is_superuser:
            return queryset
        
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(user__organization=organization)
        
        return queryset

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'occupation', 'get_children_count')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'occupation')
    filter_horizontal = ('children',)
    
    def get_queryset(self, request):
        """Filter parent profiles by organization"""
        queryset = super().get_queryset(request)
        
        if request.user.is_superuser:
            return queryset
        
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(user__organization=organization)
        
        return queryset
    
    def get_children_count(self, obj):
        return obj.children.count()
    get_children_count.short_description = 'Number of Children'

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department')
    search_fields = ('user__username', 'employee_id', 'department')
    
    def get_queryset(self, request):
        """Filter admin profiles by organization"""
        queryset = super().get_queryset(request)
        
        if request.user.is_superuser:
            return queryset
        
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(user__organization=organization)
        
        return queryset

@admin.register(ParentTeacherMessage)
class ParentTeacherMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'student', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'sender__user_type')
    search_fields = ('subject', 'message', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at', 'read_at')
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('sender', 'recipient', 'student__user')
        
        if request.user.is_superuser:
            return queryset
        
        organization = get_request_organization(request)
        if organization:
            queryset = queryset.filter(sender__organization=organization)
        
        return queryset

admin.site.register(User, CustomUserAdmin)