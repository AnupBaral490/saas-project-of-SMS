#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from saas.models import Organization

print("Deactivating other organizations...")

# Keep only organization 1 active
orgs = Organization.objects.all()
for org in orgs:
    if org.id != 1:
        print(f"Deactivating: {org.name} (ID: {org.id})")
        org.is_active = False
        org.save()
    else:
        print(f"Keeping active: {org.name} (ID: {org.id})")

print("\n✅ Done!")
