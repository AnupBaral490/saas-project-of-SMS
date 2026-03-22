#!/usr/bin/env python
"""
Debug script to check user visibility issues - why users don't show in admin_user_list
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from saas.models import Organization
from saas.utils import get_request_organization

User = get_user_model()

print("\n" + "="*70)
print(" USER VISIBILITY DEBUG - Finding Missing Users")
print("="*70)

# Test 1: Check all users in database
print("\n✅ Test 1: All Users in Database")
all_users = User.objects.all()
print(f"├─ Total users in database: {all_users.count()}")
for user in all_users:
    org_name = user.organization.name if user.organization else "NO ORGANIZATION"
    print(f"├─ {user.username} (type={user.user_type}, org={org_name})")

# Test 2: Get Sos organization
print("\n✅ Test 2: Check Sos Organization Users")
try:
    sos_org = Organization.objects.get(slug='sos-herman-gmeiner-school')
    print(f"├─ Organization: {sos_org.name} (ID={sos_org.id})")
    
    sos_users = User.objects.filter(organization=sos_org)
    print(f"├─ Users in Sos organization: {sos_users.count()}")
    for user in sos_users:
        print(f"├─ - {user.username} (type={user.user_type})")
    
except Organization.DoesNotExist:
    print("└─ Sos organization not found")

# Test 3: Check users WITHOUT organization
print("\n✅ Test 3: Users Without Organization (Potential Issue)")
orphan_users = User.objects.filter(organization__isnull=True)
print(f"├─ Users with NO organization: {orphan_users.count()}")
for user in orphan_users:
    print(f"├─ - {user.username} (type={user.user_type}) ⚠️ NOT VISIBLE IN ADMIN")

# Test 4: Simulate admin_user_list queryset
print("\n✅ Test 4: Simulate admin_user_list View")
print(f"├─ This is what the admin_user_list view will see:")

# Get Sos org
try:
    sos_org = Organization.objects.get(slug='sos-herman-gmeiner-school')
    
    # This is what get_tenant_user_queryset(request) returns
    # (assuming request picks up Sos org)
    tenant_users = User.objects.filter(organization=sos_org)
    print(f"├─ Users in Sos org: {tenant_users.count()}")
    
    # Exclude admins (like admin_user_list does)
    non_admin_users = tenant_users.exclude(user_type='admin')
    print(f"├─ Non-admin users: {non_admin_users.count()}")
    
    # Split by type
    students = non_admin_users.filter(user_type='student').count()
    teachers = non_admin_users.filter(user_type='teacher').count()
    parents = non_admin_users.filter(user_type='parent').count()
    
    print(f"├─ Students: {students}")
    print(f"├─ Teachers: {teachers}")  
    print(f"└─ Parents: {parents}")
    
except Organization.DoesNotExist:
    print("└─ Could not find Sos organization")

# Test 5: Check if recently created users lack organization
print("\n✅ Test 5: Recently Created Users")
from django.utils import timezone
from datetime import timedelta

recent_cutoff = timezone.now() - timedelta(hours=1)
recent_users = User.objects.filter(date_joined__gte=recent_cutoff)
print(f"├─ Users created in last hour: {recent_users.count()}")
for user in recent_users:
    org_status = f"ORG: {user.organization.name}" if user.organization else "❌ NO ORGANIZATION"
    print(f"├─ {user.username} (type={user.user_type}) - {org_status}")

print("\n" + "="*70)
print(" DIAGNOSIS SUMMARY")
print("="*70)

# Summary
all_count = User.objects.all().count()
with_org_count = User.objects.exclude(organization__isnull=True).count()
orphan_count = User.objects.filter(organization__isnull=True).count()

print(f"\nTotal database users: {all_count}")
print(f"├─ With organization: {with_org_count}")
print(f"└─ Without organization: {orphan_count}")

if orphan_count > 0:
    print(f"\n⚠️ ISSUE FOUND: {orphan_count} users don't have organization set!")
    print("These users WON'T show in admin_user_list because:")
    print("1. get_tenant_user_queryset filters by organization")
    print("2. NULL organization gets filtered out")
    print("\nSOLUTION: Set organization field when creating users!")
else:
    print(f"\n✓ All users have organization properly set")

print("\n" + "="*70 + "\n")
