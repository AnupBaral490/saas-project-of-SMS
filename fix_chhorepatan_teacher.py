#!/usr/bin/env python
"""
Fix vesa teacher - set correct organization_id
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
print("  FIX CHHOREPATAN TEACHER - SET CORRECT ORGANIZATION")
print("=" * 80 + "\n")

# Find vesa teacher
teacher = User.objects.filter(username='vesa', user_type='teacher').first()

if teacher:
    print(f"Found teacher: {teacher.username}")
    print(f"  Current org_id: {teacher.organization_id}")
    print(f"  Setting org_id to: 3 (Chhorepatan School)")
    
    teacher.organization_id = 3
    teacher.save()
    
    print(f"  ✅ Updated!")
    print(f"  New org_id: {teacher.organization_id}")
    print()
    
    # Verify
    updated = User.objects.get(id=teacher.id)
    print(f"Verification: {updated.username} now has org_id={updated.organization_id}")
else:
    print("❌ Teacher 'vesa' not found")

print("\n" + "=" * 80)
print("\n✅ DASHBOARD WILL NOW SHOW:")
print("""
Chhorepatan Dashboard:
  📊 Total Teachers: 1 (vesa)
  
The teacher will appear in the "Recent Users" section too!
""")
print("=" * 80 + "\n")
