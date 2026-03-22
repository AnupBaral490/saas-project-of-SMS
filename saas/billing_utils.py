"""
Stripe Payment Processing Utilities for SaaS Subscription Management
"""
import stripe
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripePaymentProcessor:
    """Handles Stripe payment operations"""

    @staticmethod
    def create_customer(organization):
        """Create a Stripe customer for organization"""
        try:
            customer = stripe.Customer.create(
                email=organization.contact_email,
                name=organization.name,
                description=f'Org: {organization.slug}',
                metadata={
                    'organization_id': organization.id,
                    'organization_slug': organization.slug,
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            return None

    @staticmethod
    def get_or_create_customer(organization):
        """Get existing Stripe customer or create new one"""
        from saas.models import Subscription
        
        sub = organization.current_subscription
        if sub and sub.external_customer_id:
            try:
                return stripe.Customer.retrieve(sub.external_customer_id)
            except stripe.error.StripeError:
                pass
        
        return StripePaymentProcessor.create_customer(organization)

    @staticmethod
    def create_payment_method(organization, card_token):
        """Create a payment method from card token"""
        try:
            customer = StripePaymentProcessor.get_or_create_customer(organization)
            if not customer:
                raise Exception("Could not create/retrieve customer")
            
            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={"token": card_token}
            )
            
            stripe.PaymentMethod.attach(
                payment_method.id,
                customer=customer.id,
            )
            
            # Set as default
            stripe.Customer.modify(
                customer.id,
                invoice_settings={
                    "default_payment_method": payment_method.id,
                }
            )
            
            return payment_method
        except stripe.error.StripeError as e:
            logger.error(f"Error creating payment method: {str(e)}")
            return None

    @staticmethod
    def create_subscription(organization, plan, payment_method=None):
        """Create a Stripe subscription"""
        try:
            from saas.models import Subscription as SubModel
            
            customer = StripePaymentProcessor.get_or_create_customer(organization)
            if not customer:
                raise Exception("Could not create/retrieve customer")
            
            # Get or create Stripe product and price
            stripe_price = StripePaymentProcessor.get_or_create_price(plan)
            if not stripe_price:
                raise Exception("Could not create Stripe price")
            
            params = {
                'customer': customer.id,
                'items': [{'price': stripe_price.id}],
                'payment_settings': {
                    'save_default_payment_method': 'on_subscription',
                },
                'metadata': {
                    'organization_id': organization.id,
                    'plan_id': plan.id,
                }
            }
            
            if plan.trial_days:
                params['trial_period_days'] = plan.trial_days
            
            subscription = stripe.Subscription.create(**params)
            
            # Save to database
            sub_model = SubModel.objects.create(
                organization=organization,
                plan=plan,
                status='trial' if plan.trial_days else 'active',
                external_customer_id=customer.id,
                external_subscription_id=subscription.id,
                starts_at=timezone.now(),
                trial_ends_at=timezone.now() + timedelta(days=plan.trial_days) if plan.trial_days else None,
                current_period_end=timezone.datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                )
            )
            
            return subscription, sub_model
        except stripe.error.StripeError as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return None, None

    @staticmethod
    def get_or_create_price(plan):
        """Get or create Stripe price for plan"""
        try:
            # Get or create product
            product = StripePaymentProcessor.get_or_create_product(plan)
            if not product:
                raise Exception("Could not create product")
            
            # Look up price
            prices = stripe.Price.list(product=product.id, active=True, limit=1)
            
            if prices.data:
                return prices.data[0]
            
            # Create new price
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan.price * 100),  # Convert to cents
                currency='usd',
                recurring={
                    'interval': 'month' if plan.billing_cycle == 'monthly' else 'year',
                    'interval_count': 1,
                },
                metadata={
                    'plan_id': plan.id,
                    'plan_code': plan.code,
                }
            )
            
            return price
        except stripe.error.StripeError as e:
            logger.error(f"Error getting/creating price: {str(e)}")
            return None

    @staticmethod
    def get_or_create_product(plan):
        """Get or create Stripe product for plan"""
        try:
            # Check if we have product ID stored
            if hasattr(plan, 'stripe_product_id') and plan.stripe_product_id:
                return stripe.Product.retrieve(plan.stripe_product_id)
            
            # Create new product
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description,
                metadata={
                    'plan_id': plan.id,
                    'plan_code': plan.code,
                }
            )
            
            # Store product ID if we can
            try:
                plan.stripe_product_id = product.id
                plan.save()
            except:
                pass
            
            return product
        except stripe.error.StripeError as e:
            logger.error(f"Error getting/creating product: {str(e)}")
            return None

    @staticmethod
    def charge_customer(organization, amount, description=""):
        """Charge a customer directly"""
        try:
            customer = StripePaymentProcessor.get_or_create_customer(organization)
            if not customer:
                raise Exception("Could not create/retrieve customer")
            
            charge = stripe.PaymentIntent.create(
                amount=int(Decimal(str(amount)) * 100),  # Convert to cents
                currency='usd',
                customer=customer.id,
                description=description or f"Payment for {organization.name}",
                metadata={
                    'organization_id': organization.id,
                }
            )
            
            return charge
        except stripe.error.StripeError as e:
            logger.error(f"Error creating charge: {str(e)}")
            return None

    @staticmethod
    def cancel_subscription(subscription_obj):
        """Cancel a Stripe subscription"""
        try:
            if not subscription_obj.external_subscription_id:
                raise Exception("No external subscription ID")
            
            stripe.Subscription.delete(subscription_obj.external_subscription_id)
            
            subscription_obj.status = 'canceled'
            subscription_obj.save()
            
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return False

    @staticmethod
    def update_subscription_plan(subscription_obj, new_plan):
        """Update subscription to new plan"""
        try:
            if not subscription_obj.external_subscription_id:
                raise Exception("No external subscription ID")
            
            stripe_subscription = stripe.Subscription.retrieve(
                subscription_obj.external_subscription_id
            )
            
            # Get new price
            new_stripe_price = StripePaymentProcessor.get_or_create_price(new_plan)
            if not new_stripe_price:
                raise Exception("Could not create new price")
            
            # Update subscription
            updated = stripe.Subscription.modify(
                subscription_obj.external_subscription_id,
                items=[{
                    'id': stripe_subscription['items']['data'][0].id,
                    'price': new_stripe_price.id,
                }],
                metadata={
                    'plan_id': new_plan.id,
                    'plan_code': new_plan.code,
                }
            )
            
            subscription_obj.plan = new_plan
            subscription_obj.save()
            
            return updated
        except stripe.error.StripeError as e:
            logger.error(f"Error updating subscription: {str(e)}")
            return None

    @staticmethod
    def handle_webhook_event(event):
        """Handle incoming Stripe webhook events"""
        from saas.models import Subscription as SubModel, PaymentEvent, Invoice, Payment
        
        event_type = event['type']
        data = event['data']['object']
        
        try:
            if event_type == 'customer.subscription.created':
                metadata = data.get('metadata', {})
                org_id = metadata.get('organization_id')
                if org_id:
                    SubModel.objects.filter(id=org_id).update(
                        external_subscription_id=data['id'],
                        external_customer_id=data['customer'],
                    )
            
            elif event_type == 'customer.subscription.updated':
                status_map = {
                    'active': 'active',
                    'past_due': 'past_due',
                    'canceled': 'canceled',
                    'trialing': 'trial',
                }
                SubModel.objects.filter(
                    external_subscription_id=data['id']
                ).update(
                    status=status_map.get(data['status'], 'active'),
                    current_period_end=timezone.datetime.fromtimestamp(
                        data['current_period_end'], tz=timezone.utc
                    )
                )
            
            elif event_type == 'customer.subscription.deleted':
                SubModel.objects.filter(
                    external_subscription_id=data['id']
                ).update(status='canceled')
            
            elif event_type == 'invoice.paid':
                Invoice.objects.filter(
                    external_invoice_id=data['id']
                ).update(status='paid', paid_at=timezone.now())
            
            elif event_type == 'invoice.payment_failed':
                Invoice.objects.filter(
                    external_invoice_id=data['id']
                ).update(status='failed')
            
            # Record webhook event
            PaymentEvent.objects.get_or_create(
                event_type=event_type,
                external_event_id=event['id'],
                defaults={
                    'data': data,
                    'is_processed': True,
                    'processed_at': timezone.now(),
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling webhook event: {str(e)}")


class BillingService:
    """High-level billing operations"""

    @staticmethod
    @transaction.atomic
    def start_trial(organization, trial_plan):
        """Start a trial subscription"""
        from saas.models import Subscription
        
        # Cancel any existing subscriptions
        Subscription.objects.filter(
            organization=organization,
            status__in=['trial', 'active']
        ).update(status='canceled')
        
        # Create subscription
        stripe_sub, sub_model = StripePaymentProcessor.create_subscription(
            organization, trial_plan
        )
        
        if sub_model:
            logger.info(f"Trial started for {organization.name}")
            return sub_model
        
        return None

    @staticmethod
    @transaction.atomic
    def upgrade_plan(organization, new_plan, payment_method=None):
        """Upgrade organization to a new plan"""
        from saas.models import Subscription
        
        current_sub = organization.current_subscription
        
        if not current_sub:
            # Start new subscription
            return BillingService.start_trial(organization, new_plan)
        
        if current_sub.plan.price < new_plan.price:
            # Upgrading - charge difference immediately
            diff = new_plan.price - current_sub.plan.price
            # Could implement prorated charges here
        
        # Update subscription
        StripePaymentProcessor.update_subscription_plan(current_sub, new_plan)
        current_sub.plan = new_plan
        current_sub.save()
        
        logger.info(f"Plan upgraded for {organization.name} to {new_plan.name}")
        return current_sub

    @staticmethod
    def generate_invoice(organization, subscription, amount=None):
        """Generate an invoice for subscription"""
        from saas.models import Invoice
        from django.utils.text import slugify
        
        if amount is None:
            amount = subscription.plan.price
        
        # Generate invoice number
        invoice_count = Invoice.objects.count() + 1
        invoice_number = f"{invoice_count:06d}"
        
        invoice = Invoice.objects.create(
            organization=organization,
            subscription=subscription,
            invoice_number=invoice_number,
            amount=amount,
            total_amount=amount,
            status='pending',
            description=f"{subscription.plan.name} - {subscription.plan.billing_cycle}",
            due_date=timezone.now().date() + timedelta(days=30),
        )
        
        logger.info(f"Invoice {invoice_number} generated for {organization.name}")
        return invoice

    @staticmethod
    def check_trial_expiration():
        """Check for expired trials and update status"""
        from saas.models import Subscription
        
        expired = Subscription.objects.filter(
            trial_ends_at__lt=timezone.now(),
            status='trial'
        ).update(status='active')
        
        return expired

    @staticmethod
    def check_overdue_invoices():
        """Check for overdue invoices and update subscription status"""
        from saas.models import Invoice, Subscription
        
        overdue_invoices = Invoice.objects.filter(
            status='pending',
            due_date__lt=timezone.now().date()
        )
        
        for invoice in overdue_invoices:
            sub = invoice.subscription
            if sub:
                sub.status = 'past_due'
                sub.save()
        
        return overdue_invoices.count()
