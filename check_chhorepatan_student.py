#!/usr/bin/env python
"""
Check where Chhorepatan students are stored
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User
from saas.db_router import clear_tenant_db

clear_tenant_db()

print("\n" + "=" * 80)
print("  WHERE IS THE CHHOREPATAN STUDENT?")
print("=" * 80 + "\n")

# Check all students by organization
print("Students by Organization:")
print("-" * 80)

for org_id in [1, None]:
    students = User.objects.filter(user_type='student', organization_id=org_id).order_by('-date_joined')
    org_name = f"Org ID {org_id}" if org_id else "NULL (Tenant DB)"
    print(f"\n{org_name}: {students.count()} students")
    
    if students.exists():
        for student in students[:10]:  # Show first 10
            print(f"  • {student.username:20} (org_id={student.organization_id}) | {student.date_joined.strftime('%Y-%m-%d %H:%M:%S')}")

# Get all teachers and parents too
print("\n" + "=" * 80)
print("\nAll Chhorepatan Users (org_id=3):")
print("-" * 80)

all_chhorepatan = User.objects.filter(organization_id=3)
print(f"Total Users: {all_chhorepatan.count()}\n")

for user_type in ['student', 'teacher', 'parent', 'admin']:
    count = all_chhorepatan.filter(user_type=user_type).count()
    print(f"  {user_type.upper()}: {count}")

if all_chhorepatan.exists():
    print(f"\nAll users in org_id=3:")
    for user in all_chhorepatan:
        print(f"  • {user.username:20} ({user.user_type})")

# Get all users with NULL organization (should be tent admin)
print("\n" + "=" * 80)
print("\nAll Users with organization_id=NULL:")
print("-" * 80)

null_org = User.objects.filter(organization_id__isnull=True)
print(f"Total: {null_org.count()}\n")

for user in null_org:
    print(f"  • {user.username:20} ({user.user_type})")

print("\n" + "=" * 80)
print("\n💡 ISSUE ANALYSIS:\n")

chhorepatan_students = User.objects.filter(organization_id=3, user_type='student')
if chhorepatan_students.count() == 0:
    print("""
❌ PROBLEM DETECTED:
   You added a student to Chhorepatan, but:
   - It's NOT saved with organization_id=3
   - It might have organization_id=NULL or organization_id=1

POSSIBLE CAUSES:
1. Admin form didn't set organization_id when saving
2. Student was created in default database instead of tenant_3
3. Student form has a bug in organization assignment

SOLUTION:
Need to check the admin form and ensure it:
- Sets organization_id=3 when saving to Chhorepatan
- Uses correct database context
""")
else:
    print(f"✅ Found {chhorepatan_students.count()} student(s) in Chhorepatan!")

print("=" * 80 + "\n")
