#!/usr/bin/env python
"""
Check where all the students came from
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User, StudentProfile
from saas.db_router import clear_tenant_db
from datetime import datetime, timedelta

clear_tenant_db()

print("\n" + "=" * 80)
print("  WHERE DID THE 32 STUDENTS COME FROM?")
print("=" * 80 + "\n")

# Get all students
students = User.objects.filter(user_type='student', organization_id=1).order_by('-date_joined')

print(f"Total Students in Sos School (org_id=1): {students.count()}\n")

# Group by date created
print("Students by Creation Date:")
print("-" * 80)

for student in students:
    created = student.date_joined.strftime("%Y-%m-%d %H:%M:%S")
    print(f"  • {student.username:20} | Created: {created} | Email: {student.email}")

print()

# Summary
print("=" * 80)
print("\n📊 ANALYSIS:\n")

# Find the most recent student
if students.exists():
    most_recent = students.first()
    oldest = students.last()
    
    print(f"Most Recent Student: {most_recent.username}")
    print(f"  Created: {most_recent.date_joined}")
    print(f"  Email: {most_recent.email}")
    print()
    
    print(f"Oldest Student: {oldest.username}")
    print(f"  Created: {oldest.date_joined}")
    print(f"  Email: {oldest.email}")
    print()

# Check if there are bulk-created students
print("\n" + "=" * 80)
print("\n💡 POSSIBLE SOURCES:")
print("""
1. Initial Migrations/Fixtures
   - The database may have been populated with test/sample data during setup
   - These 31 students were likely created before you added your own student

2. Your Recent Addition
   - The 1 student you just added is now in the list
   - Should be the most recent one in the list above

3. To Verify Your Student:
   - Look for the most recently created student above
   - That should be the one you just added

TO FIX THIS (Options):

Option A: Keep all 32 students
  - Nothing to do, they're all Sos school students (org_id=1)
  - Dashboard is correctly showing Sos school data

Option B: Delete the 31 old test students
  - Run: python manage.py shell
  - Then: User.objects.filter(organization_id=1, 
          user_type='student').exclude(username='<YOUR_NEW_STUDENT>').delete()
""")

print("=" * 80 + "\n")
