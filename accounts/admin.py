from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django.urls import reverse
from saas.utils import get_request_organization
from saas.db_router import get_tenant_db
from .models import User, StudentProfile, TeacherProfile, ParentProfile, AdminProfile, ParentTeacherMessage


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(required=True)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'organization', 'user_type', 'is_active')
    list_filter = ('organization', 'user_type', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'organization__name', 'organization__slug')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('organization', 'user_type', 'phone_number', 'address', 'date_of_birth', 'profile_picture')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'is_staff', 'is_superuser'),
        }),
        ('Additional Info', {
            'fields': ('organization', 'phone_number', 'address', 'date_of_birth', 'profile_picture'),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)

        # Always lock organization field in tenant DBs.
        if get_tenant_db() != 'default':
            if 'organization' not in readonly:
                readonly.append('organization')
        
        # For non-superusers, make organization readonly
        if not request.user.is_superuser:
            if 'organization' not in readonly:
                readonly.append('organization')
        
        # When editing an existing object, add password change link
        if obj:
            if 'password_change_link' not in readonly:
                readonly.append('password_change_link')
        
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # In tenant DBs, auth groups/permissions live in the control-plane DB.
        if get_tenant_db() != 'default':
            form.base_fields.pop('groups', None)
            form.base_fields.pop('user_permissions', None)

        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if get_tenant_db() == 'default':
            return fieldsets

        cleaned = []
        for name, opts in fieldsets:
            fields = opts.get('fields', ())
            if isinstance(fields, tuple):
                filtered = tuple(
                    field for field in fields if field not in {'groups', 'user_permissions'}
                )
            else:
                filtered = [
                    field for field in fields if field not in {'groups', 'user_permissions'}
                ]

            if filtered:
                new_opts = dict(opts)
                new_opts['fields'] = filtered
                cleaned.append((name, new_opts))

        return cleaned

    def log_addition(self, request, obj, message):
        # Skip admin log entries in tenant DBs to avoid cross-db FK issues.
        if get_tenant_db() != 'default':
            return
        return super().log_addition(request, obj, message)

    def log_change(self, request, obj, message):
        if get_tenant_db() != 'default':
            return
        return super().log_change(request, obj, message)

    def log_deletion(self, request, obj, object_repr):
        if get_tenant_db() != 'default':
            return
        return super().log_deletion(request, obj, object_repr)
    
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

        # In tenant DBs, do not filter by organization_id (stored as NULL).
        if get_tenant_db() != 'default':
            return queryset
        
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
        # In tenant DBs, store organization_id as NULL to avoid cross-db FK.
        if get_tenant_db() != 'default':
            obj.organization = None
            obj.organization_id = None
        else:
            organization = get_request_organization(request)
            if not change and organization:
                obj.organization = organization
                obj.organization_id = organization.id
        
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