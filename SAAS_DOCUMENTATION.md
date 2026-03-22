# Student Management System - SaaS Multi-Subscription Infrastructure

## Overview

This document provides a complete guide to the SaaS subscription-based model implemented in the Student Management System. The system supports multiple organizations (tenants), subscription tiers, payment processing, and comprehensive billing management.

## Architecture

### Core Components

1. **Multi-Tenancy Layer**
   - `Organization` model: Represents each customer/school
   - `OrganizationDomain`: Maps domains to organizations
   - `TenantMiddleware`: Extracts organization from request
   - All application data is scoped to organization (ForeignKey)

2. **Subscription Management**
   - `SubscriptionPlan`: Defines pricing tiers (Free, Starter, Professional, Enterprise)
   - `Subscription`: Links organization to plan with status tracking
   - Trial periods, billing cycles, and expiration handling
   - Feature flags per plan level

3. **Payment Processing**
   - `PaymentMethod`: Stores payment instruments (cards, banks, etc.)
   - `Payment`: Records individual payment transactions
   - `Invoice`: Billing records with status tracking
   - `PaymentEvent`: Webhook events from payment processors

4. **Billing Service**
   - Stripe integration for payment processing
   - Automatic invoice generation
   - Trial expiration and subscription status updates
   - Webhook handling for payment events

## Subscription Plans

### Plan Tiers

```
Free Plan
- $0/month
- 50 students, 5 teachers, 1 admin
- Features: Attendance, Grades
- No trial period

Starter Plan
- $29.99/month
- 500 students, 20 teachers, 3 admins
- Features: Attendance, Grades, Fee Management
- 14-day trial

Professional Plan
- $99.99/month (RECOMMENDED)
- 2000 students, 100 teachers, 10 admins
- Features: All Starter + Advanced Reports + API Access
- 14-day trial

Enterprise Plan
- $299.99/month
- Unlimited users
- Features: All Professional + Custom Branding + Dedicated Support
- 30-day trial
```

## User Signup Flow

### 4-Step Onboarding Process

**Step 1: Organization Creation**
- User provides organization name, subdomain, email
- Real-time subdomain availability check
- Creates `Organization` and `OrganizationDomain` records

**Step 2: Admin Account Creation**
- Creates administrator user
- Links user to organization
- Creates teacher profile for organization management

**Step 3: Plan Selection**
- Browse all available plans
- View features comparison
- Select plan and free trial period (if applicable)

**Step 4: Payment (if applicable)**
- Stripe card collection via Stripe.js
- Tokenized securely (no raw card data handled)
- Only for paid plans; free plans skip this
- Creates Stripe customer and subscription

**Result: Account Provisioned**
- User logged in automatically
- Organization fully functional
- Can invite teachers/students immediately

## Subscription Enforcement

### Decorator-Based Enforcement

```python
@subscription_required(feature='fee_management')
def fees_view(request):
    # View only accessible if subscription includes fee_management
```

### Programmatic Checks

```python
# Check if organization is within limits
is_within, remaining, message = check_subscription_limits(org, 'student')

# Check if feature is available
if org.has_feature('advanced_reports'):
    # Render advanced reports
```

### Middleware Enforcement

When users try to exceed subscription limits (e.g., adding 51st student on Free plan):
1 Middleware detects limit breach
2. Request blocked with clear error message
3. User redirected to upgrade flow

## Payment Processing with Stripe

### Integration Points

1. **Customer Creation**
   - Organization → Stripe Customer
   - Metadata linking org ID and slug
   - Reused across multiple subscriptions

2. **Subscription Creation**
   - Plan → Product → Price in Stripe
   - Automatic trial period configuration
   - Webhook IDs stored in database

3. **Webhook Handling**
   - `stripe_webhook` endpoint handles all events
   - Status updates: trial → active, past_due, canceled
   - Invoice creation and payment reconciliation
   - All events persisted in `PaymentEvent` table

### Payment Methods

- Credit/Debit Cards (Primary)
- Bank Transfers (Infrastructure in place)
- PayPal (Structure ready for integration)

## Management Commands

### Initialize Plans
```bash
python manage.py init_subscription_plans
# Creates Free, Starter, Professional, Enterprise
```

### Check Subscriptions
```bash
python manage.py check_subscriptions
# Expires trials, marks overdue invoices
# Run via cron: 0 0 * * * (daily)
```

### Generate Invoices
```bash
python manage.py generate_invoices
# Creates invoices for subscriptions due for billing
# Run via cron: 0 1 * * * (daily)

python manage.py generate_invoices --organization <org_id>
# Generate for specific organization
```

## Database Schema

### Key Models

#### Organization
```python
- id: Primary Key
- name: Organization name
- slug: URL-safe identifier
- subdomain: Unique subdomain
- contact_email: Billing email
- phone: Contact phone
- is_active: Enable/disable account
- created_at, updated_at: Timestamps
```

#### Subscription
```python
- organization: FK to Organization
- plan: FK to SubscriptionPlan
- status: trial | active | past_due | suspended | canceled
- starts_at: When subscription began
- current_period_end: Renewal date
- trial_ends_at: Trial expiration
- external_customer_id: Stripe Customer ID
- external_subscription_id: Stripe Subscription ID
```

#### Invoice
```python
- invoice_number: Unique per organization
- organization: FK to Organization
- subscription: FK to Subscription (nullable)
- amount: Line item amount
- tax: Tax amount
- total_amount: Final amount due
- status: draft | pending | paid | failed | cancelled
- issued_at: Invoice date
- due_date: Payment due date
- paid_at: When payment received
```

#### Payment
```python
- organization: FK to Organization
- invoice: FK to Invoice (nullable)
- payment_method: FK to PaymentMethod
- amount: Payment amount
- status: pending | processing | completed | failed | refunded
- external_payment_id: Stripe Payment Intent ID
```

## Configuration

### settings.py Requirements

```python
# Stripe keys (use environment variables in production)
STRIPE_PUBLIC_KEY = 'pk_test_...'  
STRIPE_SECRET_KEY = 'sk_test_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'

# Billing settings
BILLING_SETTINGS = {
    'TRIAL_DAYS': 14,
    'INVOICE_DAYS_UNTIL_DUE': 30,
    'AUTO_BILLING_ENABLED': True,
}

# Feature flags per plan
FEATURE_FLAGS = {
    'free': {...},
    'starter': {...},
    'professional': {...},
    'enterprise': {...}
}
```

### Environment Setup

#### Required Python Packages
```bash
pip install -r requirements.txt
# Includes: stripe, celery, redis, requests, python-dateutil
```

#### Stripe Account Setup
1. Create Stripe account at https://stripe.com
2. Get Public and Secret keys from Dashboard
3. Create webhook endpoint at `/billing/webhooks/stripe/`
4. Set webhook to listen for events:
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.paid
   - invoice.payment_failed
5. Copy webhook secret to settings

#### Celery/Redis (Optional, for async)
```bash
# Development (in-process):
# No additional setup needed

# Production (async tasks):
pip install celery redis
celery -A student_management_system worker --loglevel=info
redis-server
```

## URLs

### Public Pages
- `/billing/pricing/` - Pricing page
- `/billing/features/` - Features page
- `/billing/signup/` - Step 1: Create organization
- `/billing/signup/admin/` - Step 2: Create admin
- `/billing/signup/plan/` - Step 3: Choose plan
- `/billing/signup/payment/` - Step 4: Payment
- `/billing/signup/complete/` - Success page

### Authenticated Routes
- `/billing/dashboard/` - Subscription & billing dashboard
- `/billing/invoices/<id>/` - Invoice detail

### Webhooks
- `/billing/webhooks/stripe/` - Stripe webhook endpoint
- `/billing/webhooks/razorpay/` - Razorpay endpoint (future)

### API
- `/billing/api/check-subdomain/?subdomain=X` - Subdomain availability

## Security Considerations

### Data Isolation
- All queries scoped to `request.user.organization`
- TenantMiddleware enforces organization context
- No cross-organization data access possible

### Payment Security
- PCI DSS compliance via Stripe.js (no raw card data)
- Stripe tokens stored, not card numbers
- Webhook signature verification
- CSRF protection on all forms

### Admin Access
- Non-superuser admins see only their organization's data
- Superusers can cross-organizational reporting (optional)
- Organization set during login via middleware

## Testing Checklist

### Functional Testing
- [ ] User can sign up with new organization
- [ ] Trial period works correctly
- [ ] Stripe webhook processes payment events
- [ ] Subscription limits enforced (e.g., can't add 51st student on Free)
- [ ] Invoice generated correctly on billing cycle
- [ ] Overdue subscription marked as past_due
- [ ] Trial expiration transitions to active or canceled
- [ ] Admin dashboard shows correct usage metrics

### Edge Cases
- [ ] User reaches plan limit mid-request (graceful error)
- [ ] Plan change mid-billing-cycle (prorated correctly)
- [ ] Webhook received twice (idempotent handling)
- [ ] Payment fails then succeeds (correct status)
- [ ] Admin upgrades plan then downgrades (data preserved)

### Security Testing
- [ ] Can't access other organization's data via URL manipulation
- [ ] Can't escalate to superuser privileges
- [ ] Webhook signature verification prevents spoofing
- [ ] CSRF tokens required on forms

## Troubleshooting

### Subscription Not Appearing
- Check: `Organization.current_subscription` returns None?
- Run: `python manage.py check_subscriptions`
- Verify: Stripe webhook was successfully delivered

### Payment Not Processing
- Check: STRIPE_SECRET_KEY is correct
- Check: Webhook endpoint accessible from internet
- Check: Webhook signature secret matches
- Debug: Check `PaymentEvent` table for webhook data

### Users Locked Out
- Verify: Organization has active subscription
- Check: Subscription trial hasn't expired
- Check: Invoice isn't overdue (past_due status)
- Solution: Admin can manually update subscription status

### Incorrect Feature Availability
- Check: `SubscriptionPlan.feature_flags` JSON structure
- Verify: Plan assigned to subscription
- Check: `Organization.has_feature('feature_code')` returns correct value

## Production Deployment

### Pre-Production Checklist
- [ ] Stripe live keys configured (not test mode)
- [ ] STRIPE_WEBHOOK_SECRET uses live webhook
- [ ] Email notifications configured (for trial expiry, overdue, etc.)
- [ ] Payment retry logic implemented (for failed payments)
- [ ] Backup automation configured
- [ ] Usage analytics/metering implemented (optional)

### Scheduled Tasks (Cron)
```bash
# Check expirations, update statuses
0 0 * * * python manage.py check_subscriptions

# Generate invoices
0 1 * * * python manage.py generate_invoices

# Send reminders
0 10 * * * python manage.py send_billing_reminders
```

### Monitoring
- Webhook delivery success rate
- Failed payment recovery rate
- Signup funnel completion
- Churn rate by plan
- Usage metrics vs. limits

## Future Enhancements

1. **Metered Billing**
   - Track actual usage (API calls, reports generated, etc.)
   - Scale pricing to consumption

2. **Dunning Management**
   - Automatic payment retry on failure
   - Escalating email reminders
   - Graceful downgrade before suspension

3. **SSO & SAML**
   - Enterprise single sign-on
   - Directory integration

4. **Usage Analytics**
   - Dashboard showing user activity
   - Feature adoption metrics
   - Optimization recommendations

5. **Multi-currency Support**
   - Localized pricing
   - Currency-specific payment processors

6. **Coupon/Discount System**
   - Referral programmed
   - Promotional codes
   - Enterprise discounts

7. **Custom Plans**
   - Sales team can create custom tiers
   - Special pricing for large organizations
   - Feature negotiations

## Support

For issues or questions:
1. Check troubleshooting section
2. Review Stripe documentation
3. Check webhook logs in admin
4. Contact development team

---

**Last Updated:** March 2026
**Version:** 1.0
**Status:** Production Ready
