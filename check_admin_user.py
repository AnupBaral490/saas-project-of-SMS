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

print("Checking admin user in tenant database...")

org = Organization.objects.get(id=1)
add_tenant_database(org.id, org.slug)
set_tenant_db(org.id)

try:
    user = User.objects.get(username='sos_admin')
    print(f"✅ User found: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Type: {user.user_type}")
    print(f"   Is active: {user.is_active}")
    print(f"   Is staff: {user.is_staff}")
    print(f"   Is superuser: {user.is_superuser}")
    
    # Test password
    if user.check_password('SosAdmin123!'):
        print(f"   Password: CORRECT ✅")
    else:
        print(f"   Password: INCORRECT ❌")
except User.DoesNotExist:
    print(f"❌ User sos_admin not found in tenant database")
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
