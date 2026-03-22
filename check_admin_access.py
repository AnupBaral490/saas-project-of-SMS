#!/usr/bin/env python
"""
Check admin access and user credentials for Sos School
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from saas.models import Organization

User = get_user_model()
org = Organization.objects.get(slug='sos-herman-gmeiner-school')

print("\n" + "="*70)
print("CHECKING ADMIN ACCESS FOR SOS SCHOOL")
print("="*70)

# Find admin users in Sos School
admins = User.objects.filter(organization=org, user_type='admin')

print(f"\n✅ Admin Users in {org.name}:")
print(f"├─ Total admins: {admins.count()}")

for admin in admins:
    print(f"├─ Username: {admin.username}")
    print(f"├─ Email: {admin.email}")
    print(f"├─ Is staff: {admin.is_staff}")
    print(f"├─ Is superuser: {admin.is_superuser}")
    print(f"├─ Can access admin_user_list: {admin.user_type == 'admin'}")
    print()

print("\n" + "="*70)
print("HOW TO ACCESS THE STUDENT LIST")
print("="*70)
print("""
1. Login as admin: 
   - Username: (one of the admins above)
   - Password: (your admin password)

2. Visit the manage users page:
   http://localhost:8000/accounts/manage-users/

3. You should see:
   ├─ Total Users: 38
   ├─ Students: 32
   │  ├─ sadan1
   │  ├─ sadan
   │  ├─ student020
   │  └─ ... and 29 more
   ├─ Teachers: 4
   └─ Parents: 2

4. If you only see "0 Total Users":
   - Make sure you're logged in
   - Make sure you're an admin (user_type='admin')
   - Hard refresh: Ctrl+F5
   - Restart server: Stop & python manage.py runserver 8000
""")

print("="*70 + "\n")
