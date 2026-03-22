#!/usr/bin/env python
"""
Check where students are being created - default DB vs tenant DBs
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.db import connections
from accounts.models import User
from saas.models import Organization
from saas.db_router import set_tenant_db, clear_tenant_db

print("\n" + "=" * 80)
print("  CHECKING WHERE STUDENTS ARE STORED")
print("=" * 80 + "\n")

# Check default database
print("DEFAULT DATABASE (db.sqlite3):")
print("-" * 80)
clear_tenant_db()

default_students = User.objects.filter(user_type='student').count()
default_teachers = User.objects.filter(user_type='teacher').count()
default_parents = User.objects.filter(user_type='parent').count()
default_admins = User.objects.filter(user_type='admin').count()

print(f"Students: {default_students}")
print(f"Teachers: {default_teachers}")
print(f"Parents: {default_parents}")
print(f"Admins: {default_admins}")

if default_students > 0:
    print("\nAll students in DEFAULT database:")
    for user in User.objects.filter(user_type='student')[:5]:
        print(f"  - {user.username} (org_id={user.organization_id})")

print()

# Check each tenant database
organizations = Organization.objects.filter(is_active=True)

for org in organizations:
    print(f"TENANT DATABASE (tenant_{org.id}):")
    print("-" * 80)
    
    set_tenant_db(org.id)
    
    tenant_students = User.objects.filter(user_type='student').count()
    tenant_teachers = User.objects.filter(user_type='teacher').count()
    tenant_parents = User.objects.filter(user_type='parent').count()
    tenant_admins = User.objects.filter(user_type='admin').count()
    
    print(f"Organization: {org.name} (ID={org.id})")
    print(f"Students: {tenant_students}")
    print(f"Teachers: {tenant_teachers}")
    print(f"Parents: {tenant_parents}")
    print(f"Admins: {tenant_admins}")
    
    if tenant_students > 0:
        print(f"\nStudents in {org.name}:")
        for user in User.objects.filter(user_type='student')[:5]:
            print(f"  - {user.username} (org_id={user.organization_id})")
    
    print()

print("=" * 80)
print("\n💡 ANALYSIS:")
print("   If all students are in DEFAULT database:")
print("   → Students are being created in wrong database")
print("   → Need to fix admin create_user function")
print()
print("   If students are split between databases:")
print("   → Database routing is working correctly")
print()
print("=" * 80 + "\n")
