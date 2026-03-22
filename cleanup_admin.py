#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from accounts.models import User
from saas.db_router import clear_tenant_db

# Make sure we're using default database
clear_tenant_db()

print("Checking admin users in default database...")

# Find all sos_admin users
users = User.objects.filter(username='sos_admin')
print(f"Found {users.count()} sos_admin users in default database")

for user in users:
    print(f"Deleting: {user.username} (ID: {user.id}, Type: {user.user_type})")
    user.delete()

print("\n✅ Cleanup complete. Admin user removed from default database.")
print("Now admin is ONLY in tenant database (complete isolation)")

