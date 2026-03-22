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

# Register the database in settings
org = Organization.objects.get(id=1)
add_tenant_database(org.id, org.slug)

# Set tenant database
set_tenant_db(org.id)

# Check if admin user exists
admin = User.objects.filter(username='sos_admin').first()

if admin:
    print("✅ Setup SUCCESSFUL!")
    print(f"Admin user found: {admin.username} ({admin.email})")
    print(f"Organization: {admin.organization}")
    print(f"User type: {admin.user_type}")
    print(f"Is superuser: {admin.is_superuser}")
    print(f"Is staff: {admin.is_staff}")
    
    # Count tables in tenant database
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
        table_count = cursor.fetchone()[0]
    print(f"\nDatabase tables created: {table_count}")
else:
    print("❌ Setup FAILED - Admin user not found")
