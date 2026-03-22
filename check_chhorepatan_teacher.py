#!/usr/bin/env python
"""
Check where the Chhorepatan teacher was saved
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
print("  WHERE IS THE CHHOREPATAN TEACHER?")
print("=" * 80 + "\n")

# Check all teachers by organization
print("Teachers by Organization:")
print("-" * 80)

for org_id in [1, None]:
    teachers = User.objects.filter(user_type='teacher', organization_id=org_id).order_by('-date_joined')
    org_name = f"Org ID {org_id}" if org_id else "NULL (No Organization)"
    print(f"\n{org_name}: {teachers.count()} teachers")
    
    if teachers.exists():
        for teacher in teachers[:10]:
            print(f"  • {teacher.username:20} (org_id={teacher.organization_id})")

# Get all Chhorepatan users
print("\n" + "=" * 80)
print("\nAll Chhorepatan Users (org_id=3):")
print("-" * 80)

all_chhorepatan = User.objects.filter(organization_id=3)
print(f"Total Users: {all_chhorepatan.count()}\n")

for user_type in ['student', 'teacher', 'parent', 'admin']:
    count = all_chhorepatan.filter(user_type=user_type).count()
    print(f"  {user_type.upper()}: {count}")

print("\n" + "=" * 80)
print("\n💡 ANALYSIS:\n")

chhorepatan_teachers = User.objects.filter(organization_id=3, user_type='teacher')
if chhorepatan_teachers.count() == 0:
    print("""
❌ PROBLEM:
   Teacher was NOT saved with organization_id=3
   
SOLUTION:
   Same fix as before - need to ensure admin form sets
   organization_id when creating teachers
""")
else:
    print(f"✅ Found {chhorepatan_teachers.count()} teacher(s) in Chhorepatan!")

print("=" * 80 + "\n")
