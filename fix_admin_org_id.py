#!/usr/bin/env python
"""
Fix admin user organization_id for proper middleware routing
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User
from saas.models import Organization
from saas.db_router import clear_tenant_db

# Always use default database for this operation
clear_tenant_db()

print("\n" + "=" * 80)
print("  FIX ADMIN USER ORGANIZATION_ID")
print("=" * 80 + "\n")

# Map admin usernames to their organizations
admin_org_mapping = {
    'sos_admin': 1,
    'chhorepatan_admin': 3,
}

for username, org_id in admin_org_mapping.items():
    user = User.objects.filter(username=username).first()
    org = Organization.objects.get(id=org_id)
    
    if user:
        user.organization_id = org_id
        user.save()
        print(f"✅ {username}")
        print(f"   Organization: {org.name} (ID={org_id})")
        print(f"   Organization ID updated: {user.organization_id}")
        print()
    else:
        print(f"❌ {username} not found")
        print()

print("=" * 80)
print("\n✨ All admin users now have correct organization_id!")
print("   Middleware will now route requests to the correct tenant database")
print("\n" + "=" * 80 + "\n")
