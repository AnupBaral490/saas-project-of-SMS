#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.conf import settings

print("Configured databases:")
for db_name in settings.DATABASES:
    db_config = settings.DATABASES[db_name]
    print(f"\n  {db_name}:")
    print(f"    Engine: {db_config.get('ENGINE', 'N/A')}")
    print(f"    Name: {db_config.get('NAME', 'N/A')}")
