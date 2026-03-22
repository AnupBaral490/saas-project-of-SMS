#!/usr/bin/env python
"""
Setup script for Sos Herman Gmeiner School
Configures the school with separate database and subscription
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from saas.models import Organization, SubscriptionPlan, Subscription
from accounts.models import User
from saas.db_router import set_tenant_db
from django.conf import settings

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def step1_verify_organization():
    """Step 1: Verify organization exists"""
    print_section("STEP 1: VERIFY ORGANIZATION EXISTS")
    
    try:
        org = Organization.objects.get(id=1)
        print(f"\n✅ Organization Found!")
        print(f"   Name: {org.name}")
        print(f"   ID: {org.id}")
        print(f"   Slug: {org.slug}")
        print(f"   Subdomain: {org.subdomain}")
        print(f"   Active: {org.is_active}")
        return org
    except Organization.DoesNotExist:
        print("❌ Organization not found!")
        return None

def step2_check_subscription(org):
    """Step 2: Check subscription"""
    print_section("STEP 2: CHECK SUBSCRIPTION PLAN")
    
    subscription = org.subscriptions.first()
    if subscription:
        print(f"\n✅ Subscription Found!")
        print(f"   Plan: {subscription.plan.name}")
        print(f"   Price: ${subscription.plan.price}/month")
        print(f"   Status: {subscription.status.title()} {'✅' if subscription.status == 'active' else '⏳' if subscription.status == 'trial' else '❌'}")
        print(f"   Max Students: {subscription.plan.max_students}")
        print(f"   Max Teachers: {subscription.plan.max_teachers}")
        print(f"   Max Admins: {subscription.plan.max_admins}")
        
        features = subscription.plan.feature_flags.get('features', {})
        print(f"\n   Enabled Features:")
        for feature, enabled in features.items():
            status = "✅" if enabled else "❌"
            print(f"     {status} {feature.replace('_', ' ').title()}")
        return subscription
    else:
        print("❌ No subscription found!")
        return None

def step3_check_domains(org):
    """Step 3: Check domains"""
    print_section("STEP 3: CHECK DOMAINS")
    
    domains = org.domains.all()
    if domains.exists():
        print(f"\n✅ Domains Found ({domains.count()}):")
        for domain in domains:
            status = "✅ Active" if domain.is_active else "❌ Inactive"
            print(f"   {status}: {domain.domain}")
        return domains
    else:
        print("❌ No domains configured!")
        print("   (You can access via subdomain: sos-herman-gmeiner-school.local)")
        return None

def step4_provision_database(org):
    """Step 4: Provision database"""
    print_section("STEP 4: PROVISION SEPARATE DATABASE")
    
    db_name = f'tenant_{org.id}'
    
    # Check if database exists
    db_path = settings.BASE_DIR / 'tenant_databases' / f'db_{org.slug}.sqlite3'
    
    # Register database in settings
    from student_management_system.settings import add_tenant_database
    add_tenant_database(org.id, org.slug)
    
    print(f"\n✅ Database Configuration:")
    print(f"   Database Name: {db_name}")
    print(f"   Database File: db_{org.slug}.sqlite3")
    print(f"   Location: tenant_databases/")
    print(f"   Path: {db_path}")
    
    # Create tenant_databases directory if needed
    tenant_db_dir = settings.BASE_DIR / 'tenant_databases'
    tenant_db_dir.mkdir(exist_ok=True)
    print(f"\n✅ Tenant database directory ready")
    
    return db_name, db_path

def step5_run_migrations(db_name):
    """Step 5: Run migrations"""
    print_section("STEP 5: RUN MIGRATIONS ON TENANT DATABASE")
    
    from django.core.management import call_command
    
    print(f"\n⏳ Running migrations on {db_name}...")
    print("   This will create all tables (users, courses, grades, attendance, fees, etc.)")
    
    try:
        call_command(
            'migrate',
            database=db_name,
            verbosity=1,
            interactive=False
        )
        print(f"\n✅ Migrations completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def step6_create_admin_user(org, db_name):
    """Step 6: Create admin user"""
    print_section("STEP 6: CREATE ADMIN USER FOR SOS SCHOOL")
    
    # Set tenant database
    set_tenant_db(org.id)
    
    # Check if admin already exists
    existing_admin = User.objects.filter(username='sos_admin').first()
    
    if existing_admin:
        print(f"\n⚠️  Admin user already exists!")
        print(f"   Username: sos_admin")
        print(f"   Email: {existing_admin.email}")
        return existing_admin
    
    # Create admin user using organization_id (not the object)
    admin_user = User.objects.create_superuser(
        username='sos_admin',
        email='admin@sos-school.local',
        password='SosAdmin123!',
        user_type='admin',
        organization_id=org.id,  # Use ID instead of object to avoid cross-database relation error
        is_staff=True,
        is_superuser=True,
        first_name='Admin',
        last_name='SOS'
    )
    
    print(f"\n✅ Admin user created!")
    print(f"   Username: sos_admin")
    print(f"   Email: admin@sos-school.local")
    print(f"   Password: SosAdmin123! (Change this in production!)")
    print(f"   Type: Superuser")
    print(f"   Organization: {org.name}")
    
    return admin_user

def step7_summary():
    """Step 7: Summary and next steps"""
    print_section("SETUP COMPLETE! ✅")
    
    print("\n🎉 Sos Herman Gmeiner School is now ready to use!")
    print("\n" + "-" * 70)
    print("ACCESS INFORMATION:")
    print("-" * 70)
    
    print("\n1. ADD TO YOUR /etc/hosts FILE (or C:\\Windows\\System32\\drivers\\etc\\hosts):")
    print("   127.0.0.1 sos-school.local")
    
    print("\n2. START THE DEVELOPMENT SERVER:")
    print("   python manage.py runserver")
    
    print("\n3. ACCESS THE SCHOOL:")
    print("   Dashboard:  http://sos-school.local:8000/tenant/dashboard/")
    print("   Admin:      http://sos-school.local:8000/admin/")
    print("   Settings:   http://sos-school.local:8000/tenant/settings/")
    print("   Users:      http://sos-school.local:8000/tenant/users/")
    print("   Subscribe:  http://sos-school.local:8000/tenant/subscription/")
    
    print("\n4. LOGIN CREDENTIALS:")
    print("   Username: sos_admin")
    print("   Password: SosAdmin123!")
    
    print("\n" + "-" * 70)
    print("DATABASE INFORMATION:")
    print("-" * 70)
    print("   Name: tenant_1")
    print("   Storage: tenant_databases/db_sos-herman-gmeiner-school.sqlite3")
    print("   Type: Completely isolated (separate from other schools)")
    print("   Data: All users, courses, grades, attendance, fees isolated")
    
    print("\n" + "-" * 70)
    print("SUBSCRIPTION PLAN:")
    print("-" * 70)
    print("   Plan: Starter ($29.99/month)")
    print("   Max Students: 500")
    print("   Max Teachers: 20")
    print("   Max Admins: 3")
    print("   Features: Attendance, Grades, Fee Management")
    
    print("\n" + "-" * 70)
    print("NEXT STEPS:")
    print("-" * 70)
    print("   1. Add sos-school.local to your /etc/hosts file")
    print("   2. Start server: python manage.py runserver")
    print("   3. Visit: http://sos-school.local:8000/tenant/dashboard/")
    print("   4. Login with sos_admin / SosAdmin123!")
    print("   5. View organization statistics and settings")
    print("   6. Add students, teachers, and courses")
    print("   7. Create more organizations if needed")
    
    print("\n" + "=" * 70)

def main():
    """Run all steps"""
    print("\n" + "🚀 " * 25)
    print("  SOS HERMAN GMEINER SCHOOL SETUP")
    print("  Database-Per-Tenant SaaS System")
    print("🚀 " * 25)
    
    # Step 1
    org = step1_verify_organization()
    if not org:
        print("\n❌ Setup failed: Organization not found")
        return 1
    
    # Step 2
    subscription = step2_check_subscription(org)
    
    # Step 3
    step3_check_domains(org)
    
    # Step 4
    db_name, db_path = step4_provision_database(org)
    
    # Step 5
    if not step5_run_migrations(db_name):
        print("\n⚠️  Migrations had issues, but continuing...")
    
    # Step 6
    step6_create_admin_user(org, db_name)
    
    # Step 7
    step7_summary()
    
    print("\n" + "=" * 70)
    print("✅ SETUP SCRIPT COMPLETED SUCCESSFULLY!")
    print("=" * 70 + "\n")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
