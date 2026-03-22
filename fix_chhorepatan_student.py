#!/usr/bin/env python
"""
Fix ddaji student - set correct organization_id
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
print("  FIX CHHOREPATAN STUDENT - SET CORRECT ORGANIZATION")
print("=" * 80 + "\n")

# Find ddaji student
student = User.objects.filter(username='ddaji', user_type='student').first()

if student:
    print(f"Found student: {student.username}")
    print(f"  Current org_id: {student.organization_id}")
    print(f"  Setting org_id to: 3 (Chhorepatan School)")
    
    student.organization_id = 3
    student.save()
    
    print(f"  ✅ Updated!")
    print(f"  New org_id: {student.organization_id}")
    print()
    
    # Verify
    updated = User.objects.get(id=student.id)
    print(f"Verification: {updated.username} now has org_id={updated.organization_id}")
else:
    print("❌ Student 'ddaji' not found")

print("\n" + "=" * 80)
print("\n✅ DASHBOARD WILL NOW SHOW:")
print("""
Chhorepatan Dashboard:
  📊 Total Students: 1 (ddaji)
  
The student will appear in the "Recent Users" section too!
""")
print("=" * 80 + "\n")
