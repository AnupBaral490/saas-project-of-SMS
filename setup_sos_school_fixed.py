#!/usr/bin/env python
"""
Fixed setup script for Sos Herman Gmeiner School
Explicitly initializes the tenant database instead of relying on router
"""
import os
import sys
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.core.management import call_command
from django.db import connections
from saas.models import Organization
from accounts.models import User
from saas.db_router import set_tenant_db
from django.conf import settings
from pathlib import Path
from student_management_system.settings import add_tenant_database

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    print("\n" + "~" * 70)
    print("  SOS HERMAN GMEINER SCHOOL SETUP (FIXED)")
    print("  Database-Per-Tenant SaaS System")
    print("~" * 70)
    
    try:
        # Get organization
        print_section("STEP 1: VERIFY ORGANIZATION")
        org = Organization.objects.get(id=1)
        print(f"✅ Organization: {org.name} (ID={org.id})")
        
        # Get subscription
        print_section("STEP 2: CHECK SUBSCRIPTION")
        subscription = org.subscriptions.first()
        print(f"✅ Plan: {subscription.plan.name} ({subscription.status.upper()})")
        
        # Get domains
        print_section("STEP 3: CHECK DOMAINS")
        domains = org.domains.all()
        print(f"✅ Domains: {', '.join([d.domain for d in domains])}")
        
        # Provision database
        print_section("STEP 4: PROVISION DATABASE")
        db_name = f'tenant_{org.id}'
        db_file = settings.BASE_DIR / 'tenant_databases' / f'db_{org.slug}.sqlite3'
        
        # Add to settings
        add_tenant_database(org.id, org.slug)
        print(f"✅ Database configured: {db_name}")
        print(f"   File: {db_file}")
        
        # Create directory
        db_file.parent.mkdir(exist_ok=True)
        
        # Create database file if it doesn't exist
        if not db_file.exists():
            print(f"   Creating new database file...")
            sqlite3.connect(str(db_file)).close()
        
        # IMPORTANT: Close any existing connections to allow fresh setup
        db_alias = db_name
        if db_alias in connections.databases:
            connection = connections[db_alias]
            connection.close()
        
        # Migrate using explicit database
        print_section("STEP 5: RUN MIGRATIONS")
        print(f"⏳ Running migrations on {db_name}...")
        
        # Set the tenant in thread-local storage temporarily
        set_tenant_db(org.id)
        
        call_command(
            'migrate',
            database=db_name,
            verbosity=2,
            interactive=False
        )
        
        print(f"✅ Migrations completed")
        
        # Verify tables were created
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        print(f"   Tables created: {table_count}")
        
        if table_count == 0:
            print("⚠️  WARNING: No tables created. Migrations may have failed.")
            return 1
        
        # Create admin user
        print_section("STEP 6: CREATE ADMIN USER")
        
        # Ensure we're using the right database for user creation
        existing = User.objects.filter(username='sos_admin').first()
        if not existing:
            admin = User.objects.create_superuser(
                username='sos_admin',
                email='admin@sos-school.local',
                password='SosAdmin123!',
                user_type='admin',
                organization_id=org.id,
                first_name='Admin',
                last_name='SOS'
            )
            print(f"✅ Admin user created: {admin.username}")
        else:
            print(f"⚠️  Admin user already exists: sos_admin")
        
        # Summary
        print_section("SETUP COMPLETE")
        print("""
✅ SUCCESS! Sos Herman Gmeiner School is ready.

LOGIN CREDENTIALS:
  Username: sos_admin
  Password: SosAdmin123!

DATABASE:
  Name: tenant_1
  File: tenant_databases/db_sos-herman-gmeiner-school.sqlite3
  Tables: Fully isolated from other schools

NEXT STEPS:
  1. Add to /etc/hosts: 127.0.0.1 sos-school.local
  2. Run: python manage.py runserver
  3. Visit: http://sos-school.local:8000/tenant/dashboard/
        """)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
