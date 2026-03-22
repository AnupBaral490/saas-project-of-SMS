"""
Management command to generate invoices for active subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from saas.models import Subscription, Invoice, Organization
from saas.billing_utils import BillingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate invoices for active subscriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization',
            type=str,
            help='Generate invoice for specific organization ID'
        )

    def handle(self, *args, **options):
        org_id = options.get('organization')
        
        if org_id:
            # Generate invoice for specific org
            try:
                org = Organization.objects.get(id=org_id)
                subs = org.subscriptions.filter(status__in=['active', 'past_due'])
            except:
                self.stdout.write(self.style.ERROR(f'Organization {org_id} not found'))
                return
        else:
            # Generate invoices for all active subscriptions due for billing
            subs = Subscription.objects.filter(status__in=['active', 'past_due'])
        
        invoice_count = 0
        for sub in subs:
            # Check if we should generate invoice
            last_invoice = sub.invoices.order_by('-issued_at').first()
            
            should_generate = False
            if not last_invoice:
                # Never invoiced, generate now
                should_generate = True
            else:
                # Check billing cycle
                if sub.plan.billing_cycle == 'monthly':
                    days_since = (timezone.now() - last_invoice.issued_at).days
                    should_generate = days_since >= 30
                elif sub.plan.billing_cycle == 'yearly':
                    days_since = (timezone.now() - last_invoice.issued_at).days
                    should_generate = days_since >= 365
            
            if should_generate:
                invoice = BillingService.generate_invoice(
                    sub.organization,
                    sub,
                    amount=sub.plan.price
                )
                invoice_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Generated invoice {invoice.invoice_number}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Generated {invoice_count} invoices')
        )
        
        logger.info(f"Invoice generation complete: {invoice_count} invoices")
