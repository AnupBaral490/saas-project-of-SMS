#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from saas.models import Organization

print("Organizations in system:")
orgs = Organization.objects.all()
for org in orgs:
    print(f"  ID: {org.id}, Name: {org.name}, Active: {org.is_active}, Slug: {org.slug}")

print(f"\nTotal: {orgs.count()} organizations")
