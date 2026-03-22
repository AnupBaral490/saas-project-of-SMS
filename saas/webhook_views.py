"""
Stripe webhook handlers for payment events
"""
import json
import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from saas.models import PaymentEvent
from saas.billing_utils import StripePaymentProcessor
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['POST'])
def stripe_webhook(request):
    """
    Stripe webhook endpoint
    Handles payment and subscription events
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    try:
        # Handle the event
        StripePaymentProcessor.handle_webhook_event(event)
        
        logger.info(f"Webhook processed: {event['type']}")
        return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def razorpay_webhook(request):
    """
    Razorpay webhook endpoint (alternative payment processor)
    """
    # Implement Razorpay webhook handling if needed
    return JsonResponse({'success': True})
