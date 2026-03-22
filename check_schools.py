#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from saas.models import Organization, Subscription

print("\n" + "=" * 80)
print("  SCHOOLS CONFIGURED IN SAAS SYSTEM")
print("=" * 80 + "\n")

orgs = Organization.objects.all().order_by('id')
for org in orgs:
    sub = org.current_subscription
    domains = org.domains.all()
    print(f"📍 SCHOOL #{org.id}: {org.name}")
    print(f"   Slug: {org.slug}")
    print(f"   Status: {'🟢 ACTIVE' if org.is_active else '🔴 INACTIVE'}")
    print(f"   Subscription: {sub.plan.name if sub else 'None'} - {sub.status if sub else 'N/A'}")
    print(f"   Domains: {', '.join(d.domain for d in domains) if domains else 'None'}")
    
    # Check if database file exists
    db_file = f"tenant_databases/db_{org.slug}.sqlite3"
    db_exists = os.path.exists(db_file)
    print(f"   Database: {db_file} {'✅' if db_exists else '❌'}")
    print()

print("=" * 80)
print("\n✅ Total Schools: {}".format(orgs.count()))
print("\n" + "=" * 80 + "\n")
