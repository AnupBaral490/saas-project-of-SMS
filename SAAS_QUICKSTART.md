# Quick Start: Running the SaaS Student Management System

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py init_subscription_plans
```

### 3. Create Stripe Test Keys
- Go to https://stripe.com/docs/testing
- Use test keys: `pk_test_...` and `sk_test_...`
- Update `settings.py`:

```python
STRIPE_PUBLIC_KEY = 'pk_test_YOUR_KEY'
STRIPE_SECRET_KEY = 'sk_test_YOUR_KEY'
STRIPE_WEBHOOK_SECRET = 'whsec_test_YOUR_KEY'
```

### 4. Start Development Server
```bash
python manage.py runserver
```

### 5. Access the System
- **Public Signup**: http://localhost:8000/billing/signup/
- **Pricing Page**: http://localhost:8000/billing/pricing/
- **Admin Panel**: http://localhost:8000/admin/

---

## Testing the Complete Flow

### Scenario 1: Free Plan Sign-Up
1. Go to http://localhost:8000/billing/signup/
2. Enter organization details (any subdomain)
3. Create admin account
4. Select "Free" plan
5. Redirected to account ready page
6. Can immediately use system

### Scenario 2: Paid Plan Trial
1. Go to http://localhost:8000/billing/signup/
2. Enter organization details
3. Create admin account
4. Select "Starter" or "Professional" plan
5. On payment page, use Stripe test card: `4242 4242 4242 4242`
6. Any future expiry date
7. Any 3-digit CVC
8. Account activated with 14-day trial
9. Can view dashboard at http://localhost:8000/billing/dashboard/

### Scenario 3: Hitting Seat Limits
1. Create organization on Free plan (50 student limit)
2. Try to add 51st student
3. System blocks: "Student limit reached"
4. User sees upgrade prompt
5. Can upgrade to Starter plan ($29.99) for 500 students

---

## Management Commands

```bash
# Initialize subscription plans (4 tiers)
python manage.py init_subscription_plans

# Daily task: Check subscriptions, expire trials, mark overdue
python manage.py check_subscriptions

# Daily task: Generate invoices for due subscriptions
python manage.py generate_invoices

# For specific organization
python manage.py generate_invoices --organization 1
```

---

## Stripe Webhook Setup (for production)

1. In Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/billing/webhooks/stripe/`
3. Select events to listen for:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`
4. Copy signing secret (`whsec_...`)
5. Update `STRIPE_WEBHOOK_SECRET` in settings.py

---

## Admin Dashboard Features

**Organizations**
- View all customers
- See subscription status
- Check usage (students, teachers, users)
- Monitor activity

**Subscriptions**
- View by organization
- See current period
- Trial countdown
- Manage cancellations

**Invoices**
- Track billing history
- Monitor payment status
- See overdue payments
- Print for records

**Payments**
- Transaction history
- Payment method tracking
- Failed payment alerts
- Refund management

---

## Key URLs

| Path | Purpose |
|------|---------|
| `/billing/signup/` | Start signup wizard |
| `/billing/pricing/` | Public pricing |
| `/billing/features/` | Feature overview |
| `/billing/dashboard/` | Subscription management (logged in) |
| `/billing/invoices/1/` | View invoice |
| `/admin/` | Django admin |

---

## Troubleshooting

### "Stripe keys not configured"
→ Add `STRIPE_PUBLIC_KEY` and `STRIPE_SECRET_KEY` to settings.py

### "Webhook not being processed"
→ Verify webhook endpoint is publicly accessible
→ Check webhook secret in settings matches Stripe dashboard

### "Students can see other org's data"
→ TenantMiddleware extracts org from request
→ All queries automatically scoped
→ Verify middleware is in MIDDLEWARE list

### "Plan limits enforced but no error message"
→ Check form/view for `organization.is_within_limits()` checks
→ Add explicit checks before form processing

---

## Architecture Overview

```
Public Site
    ↓
    ├── /signup/ → Organization → Admin User → Plan → Payment → Account Ready
    ├── /pricing/ → Plan Features & Comparison
    └── /features/ → Feature Details

Authenticated Users
    ↓
    ├── /dashboard/ → Home → Create Teachers/Students
    │                 ↓
    │         Subscribe Required Middleware
    │                 ↓
    │         Check Organization.subscription
    │
    ├── /billing/dashboard/ → View Plan, Usage, Invoices
    └── /admin/ → Manage Org, Plans, Payments (staff only)

Payment Processing
    ↓
    ├── Stripe.js (Client) → Tokenize Card
    ├── Django (Server) → Create Subscription
    ├── Stripe API → Process Payment
    ├── Webhook → Notify System
    └── Database → Update Status
```

---

## Multi-Tenant Security

Every request is scoped to organization:

```python
# Automatic via middleware/views
org = request.user.organization

# All queries filtered
Teachers.objects.filter(organization=org)
Students.objects.filter(organization=org)

# Cross-org access prevented
# User A cannot see User B's org students
```

---

## Next Steps

1. **Test Complete Flow**
   - Sign up with test stripe key
   - Create sample data
   - Verify dashboard

2. **Configure Emails** (optional)
   - Set up email backend (Gmail, SendGrid, etc.)
   - Add invoice delivery emails
   - Add payment reminders

3. **Set Up Cron** (production)
   ```bash
   # Check subscriptions daily
   0 0 * * * /path/to/manage.py check_subscriptions
   
   # Generate invoices daily
   0 1 * * * /path/to/manage.py generate_invoices
   ```

4. **Production Deployment**
   - Switch to live Stripe keys
   - Update allowed hosts
   - Enable HTTPS
   - Set DEBUG=False
   - Configure static/media files

5. **Monitor Usage**
   - Check admin dashboard regularly
   - Review failed payment alerts
   - Monitor webhook delivery

---

## Documentation

For comprehensive documentation see: `SAAS_DOCUMENTATION.md`

---

**Status**: ✅ Production Ready  
**Last Updated**: March 2026  
**Support**: See SAAS_DOCUMENTATION.md for troubleshooting
