"""
Management command to initialize default subscription plans
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from saas.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Initialize default subscription plans'

    def handle(self, *args, **options):
        plans_data = [
            {
                'code': 'free',
                'name': 'Free',
                'description': 'Perfect for small schools starting out',
                'billing_cycle': 'monthly',
                'price': Decimal('0.00'),
                'trial_days': 0,
                'max_students': 50,
                'max_teachers': 5,
                'max_admins': 1,
                'feature_flags': {
                    'attendance_tracking': True,
                    'grade_management': True,
                    'fee_management': False,
                    'advanced_reports': False,
                    'api_access': False,
                },
            },
            {
                'code': 'starter',
                'name': 'Starter',
                'description': 'Great for growing schools',
                'billing_cycle': 'monthly',
                'price': Decimal('29.99'),
                'trial_days': 14,
                'max_students': 500,
                'max_teachers': 20,
                'max_admins': 3,
                'feature_flags': {
                    'attendance_tracking': True,
                    'grade_management': True,
                    'fee_management': True,
                    'advanced_reports': False,
                    'api_access': False,
                },
            },
            {
                'code': 'professional',
                'name': 'Professional',
                'description': 'For larger educational institutions',
                'billing_cycle': 'monthly',
                'price': Decimal('99.99'),
                'trial_days': 14,
                'max_students': 2000,
                'max_teachers': 100,
                'max_admins': 10,
                'feature_flags': {
                    'attendance_tracking': True,
                    'grade_management': True,
                    'fee_management': True,
                    'advanced_reports': True,
                    'api_access': True,
                },
            },
            {
                'code': 'enterprise',
                'name': 'Enterprise',
                'description': 'Unlimited everything with dedicated support',
                'billing_cycle': 'monthly',
                'price': Decimal('299.99'),
                'trial_days': 30,
                'max_students': None,
                'max_teachers': None,
                'max_admins': None,
                'feature_flags': {
                    'attendance_tracking': True,
                    'grade_management': True,
                    'fee_management': True,
                    'advanced_reports': True,
                    'api_access': True,
                    'custom_branding': True,
                    'dedicated_support': True,
                },
            },
        ]
        
        created_count = 0
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                code=plan_data['code'],
                defaults=plan_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                self.stdout.write(f'Plan already exists: {plan.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} subscription plans')
        )
