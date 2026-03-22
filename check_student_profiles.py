#!/usr/bin/env python
"""
Check if StudentProfile records exist for newly created students
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile
from saas.models import Organization

User = get_user_model()
org = Organization.objects.get(slug='sos-herman-gmeiner-school')

# Check if users exist
sadan = User.objects.filter(username='sadan').first()
sadan1 = User.objects.filter(username='sadan1').first()

print("\n" + "="*70)
print("CHECKING SADAN AND SADAN1 STUDENTS")
print("="*70)

print(f"\n✅ User 'sadan':")
if sadan:
    print(f"├─ Found: {sadan.username} ({sadan.user_type})")
    print(f"├─ Organization: {sadan.organization.name if sadan.organization else 'NONE'}")
    print(f"├─ Email: {sadan.email}")
    
    # Check if StudentProfile exists
    profile = StudentProfile.objects.filter(user=sadan).first()
    if profile:
        print(f"├─ ✓ StudentProfile EXISTS")
        print(f"├─ Student ID: {profile.student_id}")
        print(f"├─ Guardian: {profile.guardian_name}")
    else:
        print(f"├─ ✗ NO StudentProfile (This is why it doesn't show!)")
else:
    print(f"└─ NOT FOUND in database")

print(f"\n✅ User 'sadan1':")
if sadan1:
    print(f"├─ Found: {sadan1.username} ({sadan1.user_type})")
    print(f"├─ Organization: {sadan1.organization.name if sadan1.organization else 'NONE'}")
    print(f"├─ Email: {sadan1.email}")
    
    # Check if StudentProfile exists
    profile = StudentProfile.objects.filter(user=sadan1).first()
    if profile:
        print(f"├─ ✓ StudentProfile EXISTS")
        print(f"├─ Student ID: {profile.student_id}")
        print(f"├─ Guardian: {profile.guardian_name}")
    else:
        print(f"├─ ✗ NO StudentProfile (This is why it doesn't show!)")
else:
    print(f"└─ NOT FOUND in database")

print(f"\n✅ Total StudentProfiles in Sos School:")
profiles = StudentProfile.objects.filter(user__organization=org)
print(f"├─ Count: {profiles.count()}")
if profiles.count() == 0:
    print(f"└─ ⚠️ NO StudentProfiles found - Admin dashboard shows 'No students found'")
else:
    print(f"└─ ✓ StudentProfiles exist")

print("\n" + "="*70)
print(" DIAGNOSIS")
print("="*70)
print(f"""
The issue is likely:

1. ✓ User accounts created (sadan, sadan1)
2. ✗ StudentProfile records NOT created

Why this matters:
- admin_user_list view shows user accounts (Fixed by migration)
- But the studentlist component may need StudentProfile records
- StudentProfile contains: student_id, admission_date, guardian info

Solution:
- Create StudentProfile for each student in Django admin
- OR use a management command to create StudentProfile for users

Steps to fix:
1. Go to http://localhost:8000/admin/accounts/studentprofile/
2. Click "Add Student Profile"
3. Select user: sadan
4. Fill in: student_id, admission_date, guardian info
5. Click Save
6. Repeat for sadan1
""")
print("="*70 + "\n")
