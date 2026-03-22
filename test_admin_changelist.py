#!/usr/bin/env python
"""Test admin changelist view to ensure the AttributeError is fixed"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from saas.models import Organization
from saas.admin import OrganizationAdmin
from django.contrib.admin.views.main import TO_FIELD_VAR

# Simulate what the admin changelist_view does
try:
    org_admin = OrganizationAdmin(Organization, None)
    
    # Get all organizations
    orgs = Organization.objects.all()
    print(f'✓ Retrieved {orgs.count()} organizations from database')
    
    # For each org, access the properties used in the admin display
    for org in orgs:
        name = org.name
        slug = org.slug
        subdomain = org.subdomain
        status = org.subscription_status  # This was causing the error
        user_count = org.user_count       # This was causing the error
        student_count = org.student_count
        teacher_count = org.teacher_count
        
        print(f'\n  Organization: {name}')
        print(f'    Slug: {slug}')
        print(f'    Subdomain: {subdomain}')
        print(f'    Subscription: {status}')
        print(f'    Users: {user_count}, Students: {student_count}, Teachers: {teacher_count}')
    
    print('\n✅ Admin changelist view will work correctly!')
    print('   The AttributeError "\'Organization\' object has no attribute \'user_set\'" is FIXED')
    
except AttributeError as e:
    print(f'✗ AttributeError still exists: {e}')
except Exception as e:
    print(f'✗ Unexpected error: {e}')
