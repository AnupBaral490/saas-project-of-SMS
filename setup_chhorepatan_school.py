#!/usr/bin/env python
"""
Setup script for Chhorepatan School
Configures the school with separate database and subscription
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
from saas.models import Organization, SubscriptionPlan, OrganizationDomain
from accounts.models import User, AdminProfile
from saas.db_router import set_tenant_db, clear_tenant_db
from django.conf import settings
from pathlib import Path
from student_management_system.settings import add_tenant_database

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    print("\n" + "~" * 70)
    print("  CHHOREPATAN SCHOOL SETUP")
    print("  Database-Per-Tenant SaaS System")
    print("~" * 70)
    
    try:
        # STEP 1: Create organization
        print_section("STEP 1: CREATE ORGANIZATION")
        org, created = Organization.objects.get_or_create(
            name='Chhorepatan School',
            defaults={
                'slug': 'chhorepatan-school',
                'subdomain': 'chhorepatan',
                'is_active': True,
            }
        )
        if created:
            print(f"✅ Organization created: {org.name} (ID={org.id})")
        else:
            print(f"✅ Organization already exists: {org.name} (ID={org.id})")
        
        # STEP 2: Create subscription plan
        print_section("STEP 2: CREATE SUBSCRIPTION PLAN")
        plan, created = SubscriptionPlan.objects.get_or_create(
            code='starter',
            defaults={
                'name': 'Starter',
                'price': 29.99,
                'max_students': 500,
                'max_teachers': 20,
                'max_admins': 3,
                'is_active': True,
            }
        )
        print(f"✅ Plan: {plan.name} (${plan.price}/month)")
        
        # STEP 3: Create subscription for organization
        print_section("STEP 3: ACTIVATE SUBSCRIPTION")
        from saas.models import Subscription
        subscription, created = Subscription.objects.get_or_create(
            organization=org,
            defaults={
                'plan': plan,
                'status': 'active',
            }
        )
        if created:
            print(f"✅ Subscription activated: {subscription.plan.name}")
        else:
            print(f"✅ Subscription already active: {subscription.plan.name}")
        
        # STEP 4: Create domain
        print_section("STEP 4: CREATE DOMAIN")
        domain, created = OrganizationDomain.objects.get_or_create(
            domain='chhorepatan-school.local',
            defaults={
                'organization': org,
                'is_primary': True,
                'is_active': True,
            }
        )
        if created:
            print(f"✅ Domain created: {domain.domain}")
        else:
            print(f"✅ Domain already exists: {domain.domain}")
        
        # STEP 5: Provision database
        print_section("STEP 5: PROVISION SEPARATE DATABASE")
        db_name = f'tenant_{org.id}'
        db_file = settings.BASE_DIR / 'tenant_databases' / f'db_{org.slug}.sqlite3'
        
        add_tenant_database(org.id, org.slug)
        print(f"✅ Database configured: {db_name}")
        print(f"   File: {db_file}")
        
        db_file.parent.mkdir(exist_ok=True)
        if not db_file.exists():
            print(f"   Creating new database file...")
            sqlite3.connect(str(db_file)).close()
        
        # Close any existing connections
        if db_name in connections.databases:
            connection = connections[db_name]
            connection.close()
        
        # STEP 6: Run migrations
        print_section("STEP 6: RUN MIGRATIONS")
        print(f"⏳ Running migrations on {db_name}...")
        
        set_tenant_db(org.id)
        
        call_command(
            'migrate',
            database=db_name,
            verbosity=2,
            interactive=False
        )
        
        print(f"✅ Migrations completed")
        
        # Verify tables
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
        print(f"   Tables created: {table_count}")
        
        if table_count == 0:
            print("⚠️  WARNING: No tables created. Migrations may have failed.")
            return 1
        
        # STEP 7: Create admin user
        print_section("STEP 7: CREATE ADMIN USER")
        
        existing = User.objects.filter(username='chhorepatan_admin').first()
        if not existing:
            admin = User.objects.create_superuser(
                username='chhorepatan_admin',
                email='admin@chhorepatan-school.local',
                password='ChhorepAtanAdmin123!',
                user_type='admin',
                first_name='Admin',
                last_name='Chhorepatan'
            )
            # Create admin profile
            AdminProfile.objects.create(
                user=admin,
                employee_id=f'ADM001',
                department='Administration'
            )
            print(f"✅ Admin user created: {admin.username}")
        else:
            print(f"⚠️  Admin user already exists: chhorepatan_admin")
        
        # Summary
        print_section("SETUP COMPLETE")
        print(f"""
✅ SUCCESS! Chhorepatan School is now ready to use!

ORGANIZATION INFO:
  Name: {org.name}
  ID: {org.id}
  Slug: {org.slug}
  Subscription: {subscription.plan.name} (${subscription.plan.price}/month)

DATABASE:
  Name: tenant_{org.id}
  File: {db_file}
  Tables: {table_count}

LOGIN CREDENTIALS:
  Username: chhorepatan_admin
  Password: ChhorepAtanAdmin123!
  Email: admin@chhorepatan-school.local

DOMAIN:
  {domain.domain}

NEXT STEPS:
  1. Add to /etc/hosts: 127.0.0.1 {domain.domain}
  2. Access: http://{domain.domain}:8000/tenant/dashboard/
  3. Or: http://127.0.0.1:8000/tenant/dashboard/
        """)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
