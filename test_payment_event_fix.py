#!/usr/bin/env python
"""
Test script to verify PaymentEvent admin restrictions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from django.contrib.admin.sites import AdminSite
from saas.admin import PaymentEventAdmin
from saas.models import PaymentEvent

# Test 1: Verify add permission is disabled
admin_site = AdminSite()
admin = PaymentEventAdmin(PaymentEvent, admin_site)

# Create a mock request
class MockRequest:
    def __init__(self):
        self.user = None

request = MockRequest()

has_add = admin.has_add_permission(request)
has_delete = admin.has_delete_permission(request, None)
has_change = admin.has_change_permission(request, None)

print("✅ PaymentEvent Admin Permission Tests")
print(f"├─ has_add_permission: {has_add} (should be False)")
print(f"├─ has_delete_permission: {has_delete} (should be False)")
print(f"└─ has_change_permission: {has_change} (should be True - read-only)")

# Test 2: Verify data field has default
test_event = PaymentEvent(
    event_type='charge.succeeded',
    external_event_id='test_evt_123'
)

print("\n✅ PaymentEvent Model Default Value Test")
print(f"├─ data field default: {test_event.data} (should be {{}})")
print(f"├─ data type: {type(test_event.data).__name__}")
print(f"└─ Can save without explicit data: {test_event.data == {}}")

if has_add is False and has_delete is False and has_change is True and test_event.data == {}:
    print("\n✅ All PaymentEvent admin fixes verified successfully!")
else:
    print("\n❌ Some checks failed!")
