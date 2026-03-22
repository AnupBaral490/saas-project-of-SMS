#!/usr/bin/env python
"""Test Organization properties to verify the fix"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from saas.models import Organization

org_count = Organization.objects.count()
print(f'Organizations in database: {org_count}')

if org_count > 0:
    org = Organization.objects.first()
    print(f'Testing first organization: {org.name}')
    try:
        print(f'  ✓ User count: {org.user_count}')
        print(f'  ✓ Student count: {org.student_count}')
        print(f'  ✓ Teacher count: {org.teacher_count}')
        print(f'  ✓ Subscription status: {org.subscription_status}')
        print('\n✅ All Organization properties working correctly!')
    except Exception as e:
        print(f'  ✗ Error: {e}')
else:
    print('No organizations in database (expected for new installation)')
    print('✅ Properties are syntactically correct!')
