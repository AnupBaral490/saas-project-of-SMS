#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from saas.db_router import set_tenant_db
from accounts.models import User
from saas.models import Organization
from django.conf import settings
from student_management_system.settings import add_tenant_database

# Get organization
org = Organization.objects.get(id=1)

# Register database
add_tenant_database(org.id, org.slug)

# Set tenant database
set_tenant_db(org.id)

# Create admin user (without assigning organization - it's in the other DB)
print("Creating admin user...")
try:
    admin = User.objects.create_superuser(
        username='sos_admin',
        email='admin@sos-school.local',
        password='SosAdmin123!',
        user_type='admin',
        first_name='Admin',
        last_name='SOS'
    )
    print(f"✅ Admin user created successfully!")
    print(f"   Username: {admin.username}")
    print(f"   Email: {admin.email}")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
