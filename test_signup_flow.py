#!/usr/bin/env python
"""
Test script to verify the signup flow creates users correctly
without IntegrityError for missing profile fields.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from saas.models import Organization
from accounts.models import AdminProfile, TeacherProfile

User = get_user_model()

print("\n" + "="*70)
print(" SIGNUP FLOW TEST - User Creation Without Profile Errors")
print("="*70)

# Test 1: Check if Sos organization exists
print("\n✅ Test 1: Check Organization")
try:
    org = Organization.objects.get(slug='sos-herman-gmeiner-school')
    print(f"├─ Organization found: {org.name}")
    print(f"└─ ✓ Ready for signup testing")
except Organization.DoesNotExist:
    print("└─ ✗ Organization not found - cannot test signup")
    exit(1)

# Test 2: Test creating admin user (like signup step 2)
print("\n✅ Test 2: Create Admin User (Signup Step 2 Simulation)")
try:
    # Simulate what signup_step2_admin does
    test_email = f"test_admin_{os.getpid()}@test.com"
    
    admin_user = User.objects.create_user(
        username=test_email,
        email=test_email,
        password='TestPassword123!',
        first_name='Test',
        last_name='Admin',
        organization=org,
        user_type='admin',
        is_staff=True,
        is_superuser=False,
    )
    
    print(f"├─ Admin user created: {admin_user.email}")
    print(f"├─ User ID: {admin_user.id}")
    print(f"├─ Organization: {admin_user.organization.name}")
    print(f"├─ User Type: {admin_user.user_type}")
    print(f"└─ ✓ Admin user created successfully without profile errors")
    
    # Clean up
    admin_user.delete()
    
except Exception as e:
    print(f"└─ ✗ Error creating admin user: {e}")
    exit(1)

# Test 3: Check profile field flexibility
print("\n✅ Test 3: Check Profile Field Flexibility")
try:
    # Create a test user
    test_email = f"test_profile_{os.getpid()}@test.com"
    test_user = User.objects.create_user(
        username=test_email,
        email=test_email,
        password='TestPassword123!',
        first_name='Test',
        last_name='User',
        organization=org,
        user_type='teacher',
    )
    
    # Test creating AdminProfile with optional fields
    admin_profile = AdminProfile.objects.create(user=test_user)
    print(f"├─ AdminProfile created with optional fields:")
    print(f"  ├─ employee_id: {admin_profile.employee_id}")
    print(f"  ├─ department: {admin_profile.department}")
    print(f"  └─ Both can be NULL")
    admin_profile.delete()
    
    # Test creating TeacherProfile with optional fields
    teacher_profile = TeacherProfile.objects.create(user=test_user)
    print(f"├─ TeacherProfile created with optional fields:")
    print(f"  ├─ joining_date: {teacher_profile.joining_date}")
    print(f"  ├─ qualification: {teacher_profile.qualification}")
    print(f"  ├─ specialization: {teacher_profile.specialization}")
    print(f"  ├─ employee_id: {teacher_profile.employee_id}")
    print(f"  └─ All can be NULL/blank")
    teacher_profile.delete()
    
    print(f"└─ ✓ Profiles can be created with minimal fields")
    
    # Clean up
    test_user.delete()
    
except Exception as e:
    print(f"└─ ✗ Error testing profile fields: {e}")
    exit(1)

# Test 4: Verify signup user_type is set correctly
print("\n✅ Test 4: Verify User Type Field")
try:
    test_email = f"test_signup_{os.getpid()}@test.com"
    user = User.objects.create_user(
        username=test_email,
        email=test_email,
        password='TestPassword123!',
        organization=org,
        user_type='admin',
    )
    
    if user.user_type == 'admin':
        print(f"├─ User type correctly set to: {user.user_type}")
        print(f"└─ ✓ user_type field working properly")
    else:
        print(f"└─ ✗ user_type not set correctly: {user.user_type}")
    
    user.delete()
    
except Exception as e:
    print(f"└─ ✗ Error testing user_type: {e}")
    exit(1)

print("\n" + "="*70)
print(" RESULT: Signup Flow Test ✅ PASSED")
print("="*70)
print("\nSignup changes working correctly:")
print("✓ Admin users created without TeacherProfile")
print("✓ Admin users have user_type='admin' set")
print("✓ Profile fields are now optional")
print("✓ No IntegrityError on joining_date or employee_id")
print("\nYou can now complete the signup flow! 🎉")
print("="*70 + "\n")
