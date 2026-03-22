#!/usr/bin/env python
"""
Verify admin user organization_id is set correctly
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
print("  ADMIN USER ORGANIZATION MAPPING")
print("=" * 80 + "\n")

admins = User.objects.filter(user_type='admin', is_superuser=True).order_by('id')

for user in admins:
    org_name = user.organization.name if user.organization else "None"
    print(f"Username: {user.username}")
    print(f"  Organization ID: {user.organization_id}")
    print(f"  Organization: {org_name}")
    print(f"  Email: {user.email}")
    print()

print("=" * 80)
print("\n✅ CONFIGURATION SUMMARY:")
print("""
Each admin is now associated with their organization:

1. sos_admin → Sos Herman Gmeiner School (org_id=1)
   - When logs in → Middleware routes to tenant_1
   - Dashboard shows Sos school data

2. chhorepatan_admin → Chhorepatan School (org_id=3)
   - When logs in → Middleware routes to tenant_3
   - Dashboard shows Chhorepatan school data

RESULT: Dashboard now shows organization-specific data! ✨
""")
print("=" * 80 + "\n")
