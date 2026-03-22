#!/usr/bin/env python
"""
Create sos_admin in default database (if missing)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User, AdminProfile
from saas.models import Organization
from saas.db_router import clear_tenant_db

clear_tenant_db()

print("\n" + "=" * 80)
print("  CREATE SOS ADMIN IN DEFAULT DATABASE")
print("=" * 80 + "\n")

org = Organization.objects.get(id=1)

# Check if user exists
existing = User.objects.filter(username='sos_admin').first()

if not existing:
    print("✅ Creating sos_admin...")
    user = User.objects.create_superuser(
        username='sos_admin',
        email='admin@sos-herman-gmeiner-school.local',
        password='SosAdmin123!',
        user_type='admin',
        first_name='Admin',
        last_name='Sos',
        organization_id=1
    )
    
    AdminProfile.objects.create(
        user=user,
        employee_id='ADM002',
        department='Administration'
    )
    
    print(f"   Username: {user.username}")
    print(f"   Organization: {org.name} (ID=1)")
    print(f"   Email: {user.email}")
else:
    print(f"⚠️  User already exists: {existing.username}")
    # Update organization_id if missing
    if existing.organization_id != 1:
        existing.organization_id = 1
        existing.save()
        print(f"✅ Updated organization_id to 1")

print("\n" + "=" * 80 + "\n")
