#!/usr/bin/env python
"""
Simulate what admin_user_list view returns to diagnose dashboard issue
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from saas.models import Organization
from django.db import models

User = get_user_model()

# Get Sos organization
org = Organization.objects.get(slug='sos-herman-gmeiner-school')

print("\n" + "="*70)
print("SIMULATING admin_user_list VIEW")
print("="*70)

# This is what the view does:
# get_tenant_user_queryset(request) returns users filtered by organization
base_users = User.objects.filter(organization=org).exclude(user_type='admin')

print(f"\n✅ Step 1: Filter by organization")
print(f"├─ Organization: {org.name}")
print(f"├─ Total users in org: {User.objects.filter(organization=org).count()}")
print(f"├─ Non-admin users: {base_users.count()}")

# Group by type
grouped_users = {
    'parents': base_users.filter(user_type='parent').order_by('-date_joined'),
    'teachers': base_users.filter(user_type='teacher').order_by('-date_joined'),
    'students': base_users.filter(user_type='student').order_by('-date_joined'),
}

print(f"\n✅ Step 2: Group by user type")
print(f"├─ Parents: {grouped_users['parents'].count()}")
print(f"├─ Teachers: {grouped_users['teachers'].count()}")
print(f"├─ Students: {grouped_users['students'].count()}")

# Check if sadan and sadan1 are in students
print(f"\n✅ Step 3: Check if sadan and sadan1 are in student list")
students_list = grouped_users['students']
sadan_exists = students_list.filter(username='sadan').exists()
sadan1_exists = students_list.filter(username='sadan1').exists()

print(f"├─ sadan in student list: {sadan_exists}")
print(f"├─ sadan1 in student list: {sadan1_exists}")

if sadan_exists and sadan1_exists:
    print(f"└─ ✓ Both students SHOULD appear in the dashboard")
else:
    print(f"└─ ✗ Students NOT in the queryset - investigating...")
    
    # Debug: show all students
    print(f"\n✅ Step 4: Debug - All students in student list:")
    for student in students_list[:10]:
        print(f"├─ {student.username} (org_id={student.organization_id})")
    if students_list.count() > 10:
        print(f"├─ ... and {students_list.count() - 10} more")

print("\n" + "="*70)
print(" WHAT THE DASHBOARD WOULD SHOW")
print("="*70)
print(f"""
Total Users: {grouped_users['parents'].count() + grouped_users['teachers'].count() + grouped_users['students'].count()}
Parents ({grouped_users['parents'].count()}):
""")
for parent in grouped_users['parents'][:3]:
    print(f"  - {parent.username}")
if grouped_users['parents'].count() > 3:
    print(f"  ... and {grouped_users['parents'].count() - 3} more")

print(f"""
Teachers ({grouped_users['teachers'].count()}):
""")
for teacher in grouped_users['teachers'][:3]:
    print(f"  - {teacher.username}")
if grouped_users['teachers'].count() > 3:
    print(f"  ... and {grouped_users['teachers'].count() - 3} more")

print(f"""
Students ({grouped_users['students'].count()}):
""")
for student in grouped_users['students'][:10]:
    print(f"  - {student.username}")
if grouped_users['students'].count() > 10:
    print(f"  ... and {grouped_users['students'].count() - 10} more")

print("\n" + "="*70 + "\n")
