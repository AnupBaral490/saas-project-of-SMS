#!/usr/bin/env python
"""
Delete all test students, keep only real ones (sadan, sadan1)
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
print("  DELETE TEST STUDENTS - KEEP ONLY REAL ONES")
print("=" * 80 + "\n")

# Get all students except the ones you added
test_students = User.objects.filter(
    user_type='student',
    organization_id=1
).exclude(
    username__in=['sadan', 'sadan1']
).order_by('-date_joined')

print(f"Students to DELETE: {test_students.count()}")
print("-" * 80)

for student in test_students:
    print(f"  ✗ {student.username:20} (Created: {student.date_joined.strftime('%Y-%m-%d %H:%M')})")

print("\n" + "-" * 80)
print(f"\nStudents to KEEP:")
print("-" * 80)

keep_students = User.objects.filter(
    user_type='student',
    organization_id=1,
    username__in=['sadan', 'sadan1']
).order_by('-date_joined')

for student in keep_students:
    print(f"  ✓ {student.username:20} (Created: {student.date_joined.strftime('%Y-%m-%d %H:%M')})")

print("\n" + "=" * 80)
print(f"\nDeleting {test_students.count()} test students...")

# Delete test students
deleted_count, _ = test_students.delete()

print(f"✅ DELETED: {deleted_count} objects (students + related data)")

# Verify
remaining = User.objects.filter(user_type='student', organization_id=1).count()
print(f"✅ REMAINING: {remaining} students in Sos school")

print("\n" + "=" * 80)
print("\n🎉 CLEANUP COMPLETE!")
print("""
Dashboard will now show:
  📊 Total Students: 2 (only your real students)
  
Your students:
  1. sadan
  2. sadan1
  
All test data has been removed! 🗑️
""")
print("=" * 80 + "\n")
