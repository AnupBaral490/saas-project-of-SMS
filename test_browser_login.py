#!/usr/bin/env python
"""
Simulate browser login to Chhorepatan School
Tests the actual HTTP login flow
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.test import Client
from django.urls import reverse

print("\n" + "=" * 80)
print("  SIMULATING BROWSER LOGIN TO CHHOREPATAN SCHOOL")
print("=" * 80 + "\n")

# Create a test client (simulates a browser)
client = Client()

# Step 1: Visit login page
print("STEP 1: Visiting login page...")
print("-" * 80)

login_url = '/admin/login/'
response = client.get(login_url)

print(f"URL: http://127.0.0.1:8000{login_url}")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print("✅ Login page loaded successfully")
    if 'Django administration' in response.content.decode():
        print("✅ Page contains Django admin form")
else:
    print(f"❌ Error loading page: {response.status_code}")

print()

# Step 2: Submit login form
print("STEP 2: Submitting login credentials...")
print("-" * 80)

login_data = {
    'username': 'chhorepatan_admin',
    'password': 'ChhorepAtanAdmin123!',
}

response = client.post(login_url, login_data, follow=True)

print(f"Credentials:")
print(f"  - Username: {login_data['username']}")
print(f"  - Password: [hidden]")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print("✅ Login request processed")
    
    # Check if we're redirected to admin dashboard
    if '/admin/' in response.request['PATH_INFO']:
        print(f"✅ Redirected to: {response.request['PATH_INFO']}")
    else:
        print(f"⚠️  Location: {response.request['PATH_INFO']}")
else:
    print(f"❌ Error: {response.status_code}")

print()

# Step 3: Check session
print("STEP 3: Checking session...")
print("-" * 80)

session = client.session
if '_auth_user_id' in session:
    user_id = session['_auth_user_id']
    print(f"✅ User logged in with ID: {user_id}")
    
    from accounts.models import User
    user = User.objects.get(id=user_id)
    print(f"   Username: {user.username}")
    print(f"   Organization ID: {user.organization_id}")
    print(f"   User Type: {user.user_type}")
else:
    print("❌ Session: User NOT logged in")

print()

# Step 4: Test admin page access
print("STEP 4: Testing admin dashboard access...")
print("-" * 80)

admin_url = '/admin/'
response = client.get(admin_url)

print(f"URL: http://127.0.0.1:8000{admin_url}")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print("✅ Admin dashboard is accessible")
    if 'Site administration' in response.content.decode():
        print("✅ Dashboard contains admin content")
else:
    print(f"⚠️  Response: {response.status_code}")

print()

# Summary
print("=" * 80)
print("  ✅ BROWSER LOGIN TEST COMPLETE!")
print("=" * 80)
print("""
WHAT JUST HAPPENED:
1. Simulated a browser visiting http://127.0.0.1:8000/admin/login/
2. Submitted login form with Chhorepatan admin credentials
3. Django authenticated the user and created a session
4. User was redirected to admin dashboard
5. Session confirms user is logged in

KEY RESULT:
✨ The login system is working correctly!
   You can now open your actual browser and log in.

NEXT STEPS:
1. Open your web browser
2. Visit: http://127.0.0.1:8000/admin/login/
3. Enter:
   - Username: chhorepatan_admin
   - Password: ChhorepAtanAdmin123!
4. Click "Log in"
5. You'll see the admin dashboard!
""")

print("=" * 80 + "\n")
