#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User
from saas.models import Organization
from saas.db_router import set_tenant_db
from django.conf import settings
from student_management_system.settings import add_tenant_database

print("Creating admin user in default database...")
try:
    # Create in default database
    admin = User.objects.create_superuser(
        username='sos_admin',
        email='admin@sos-school.local',
        password='SosAdmin123!',
        user_type='admin',
        first_name='Admin',
        last_name='SOS'
    )
    print(f"✅ Admin user created in default database")
except User.DoesNotExist:
    print("✅ Admin user already exists in default database")
except Exception as e:
    print(f"Error in default database: {str(e)}")

print("\nCreating admin user in tenant database...")
try:
    org = Organization.objects.get(id=1)
    add_tenant_database(org.id, org.slug)
    set_tenant_db(org.id)
    
    # Try to create in tenant database
    admin = User.objects.create_superuser(
        username='sos_admin',
        email='admin@sos-school.local',
        password='SosAdmin123!',
        user_type='admin',
        first_name='Admin',
        last_name='SOS'
    )
    print(f"✅ Admin user created in tenant database")
except Exception as e:
    if "UNIQUE constraint failed" in str(e) or "already exists" in str(e):
        print(f"✅ Admin user already exists in tenant database")
    else:
        print(f"Error in tenant database: {str(e)}")
        import traceback
        traceback.print_exc()

print("\nSetup complete! Try logging in with:")
print("  Username: sos_admin")
print("  Password: SosAdmin123!")
