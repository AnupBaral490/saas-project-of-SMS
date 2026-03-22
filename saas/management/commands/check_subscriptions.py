"""
Management command to check trial expiration and update subscription status
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from saas.models import Subscription
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check expired trials and update subscription status'

    def handle(self, *args, **options):
        # Check expired trials
        expired_count = Subscription.objects.filter(
            trial_ends_at__lt=timezone.now(),
            status='trial'
        ).update(status='active')
        
        self.stdout.write(
            self.style.SUCCESS(f'Updated {expired_count} expired trials to active')
        )
        
        # Check overdue invoices
        from saas.models import Invoice
        
        overdue = Invoice.objects.filter(
            status='pending',
            due_date__lt=timezone.now().date()
        )
        
        updated_count = 0
        for invoice in overdue:
            if invoice.subscription:
                invoice.subscription.status = 'past_due'
                invoice.subscription.save()
                updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Marked {updated_count} subscriptions as past_due')
        )
        
        logger.info(f"Subscription check complete: {expired_count} trials, {updated_count} past_due")
