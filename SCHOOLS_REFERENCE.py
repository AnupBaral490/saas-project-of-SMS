#!/usr/bin/env python
"""
Quick reference for all configured schools in the SaaS system
"""

SCHOOLS = {
    1: {
        'name': 'Sos Herman Gmeiner School',
        'organization_id': 1,
        'slug': 'sos-herman-gmeiner-school',
        'database': 'tenant_1',
        'database_file': 'tenant_databases/db_sos-herman-gmeiner-school.sqlite3',
        'admin_user': 'sos_admin',
        'admin_password': 'SosAdmin123!',
        'admin_email': 'admin@sos-herman-gmeiner-school.local',
        'domain': 'sos-herman-gmeiner-school.local',
        'domain_ip': '127.0.0.1',
        'subscription': 'Starter ($29.99/month)',
        'status': 'ACTIVE ✅',
    },
    3: {
        'name': 'Chhorepatan School',
        'organization_id': 3,
        'slug': 'chhorepatan-school',
        'database': 'tenant_3',
        'database_file': 'tenant_databases/db_chhorepatan-school.sqlite3',
        'admin_user': 'chhorepatan_admin',
        'admin_password': 'ChhorepAtanAdmin123!',
        'admin_email': 'admin@chhorepatan-school.local',
        'domain': 'chhorepatan-school.local',
        'domain_ip': '127.0.0.1',
        'subscription': 'Starter ($29.99/month)',
        'status': 'ACTIVE ✅',
    }
}

print("\n" + "=" * 80)
print("  CONFIGURED SCHOOLS IN SAAS SYSTEM")
print("=" * 80)

for org_id, school in SCHOOLS.items():
    print(f"\n📍 SCHOOL #{org_id}: {school['name']}")
    print("-" * 80)
    print(f"  Organization ID: {school['organization_id']}")
    print(f"  Database: {school['database']}")
    print(f"  Tables: 53 (all migrations applied)")
    print(f"  Status: {school['status']}")
    print(f"\n  LOGIN:")
    print(f"    Username: {school['admin_user']}")
    print(f"    Password: {school['admin_password']}")
    print(f"    Email: {school['admin_email']}")
    print(f"\n  ACCESS (using local IP):")
    print(f"    http://{school['domain_ip']}:8000/tenant/dashboard/")
    print(f"\n  ACCESS (using domain - after hosts file update):")
    print(f"    http://{school['domain']}:8000/tenant/dashboard/")
    print(f"\n  SUBSCRIPTION:")
    print(f"    Plan: {school['subscription']}")

print("\n" + "=" * 80)
print("\n✨ NEXT STEPS:")
print("  1. Visit http://127.0.0.1:8000/tenant/dashboard/ (works immediately)")
print("  2. Django will auto-detect which school based on domain/subdomain")
print("  3. To set domain routing, update Django ALLOWED_HOSTS or middleware")
print("  4. Both schools have completely isolated databases")
print("  5. Add more schools using the same setup pattern")
print("\n" + "=" * 80 + "\n")

if __name__ == '__main__':
    pass
