#!/usr/bin/env python
"""
Add Chhorepatan admin to default database for authentication
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.db import connections
from saas.models import Organization
from saas.db_router import clear_tenant_db
from accounts.models import User, AdminProfile

print("\n" + "=" * 80)
print("  ADD CHHOREPATAN ADMIN TO DEFAULT DATABASE")
print("=" * 80 + "\n")

# Ensure we're using default database
clear_tenant_db()

# Get Chhorepatan organization
org = Organization.objects.get(id=3)
print(f"Organization: {org.name} (ID={org.id})")

# Create user in DEFAULT database
existing = User.objects.filter(username='chhorepatan_admin').first()
if not existing:
    print("\n✅ Creating chhorepatan_admin in default database...")
    admin = User.objects.create_superuser(
        username='chhorepatan_admin',
        email='admin@chhorepatan-school.local',
        password='ChhorepAtanAdmin123!',
        user_type='admin',
        first_name='Admin',
        last_name='Chhorepatan'
    )
    print(f"   Username: {admin.username}")
    print(f"   Email: {admin.email}")
    print(f"   Is Superuser: {admin.is_superuser}")
    
    # Create admin profile
    AdminProfile.objects.create(
        user=admin,
        employee_id='ADM001',
        department='Administration'
    )
    print(f"   Admin Profile: Created")
else:
    print(f"\n⚠️  User already exists: {existing.username}")
    print(f"   Email: {existing.email}")
    print(f"   Is Superuser: {existing.is_superuser}")

print("\n" + "=" * 80)
print("  ✅ SETUP COMPLETE")
print("=" * 80)
print("\nNow you can login with:")
print("  Username: chhorepatan_admin")
print("  Password: ChhorepAtanAdmin123!")
print("\nVisit: http://127.0.0.1:8000/admin/login/")
print("\n" + "=" * 80 + "\n")
