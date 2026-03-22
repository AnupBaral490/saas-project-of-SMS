# Database-Per-Tenant SaaS Architecture

## Overview

This application has been converted to a **complete database-per-tenant SaaS system** where each organization (school) has:

1. **Its own isolated SQLite database file** - Complete data separation at the database level
2. **Separate domain/URL** - Each school appears on its own domain (e.g., sos-school.local, other-school.local)
3. **Completely separate dashboard** - Organization-specific views and statistics
4. **Automatic database routing** - Middleware automatically routes all queries to the correct tenant database

## Architecture Components

### 1. Database Router (`saas/db_router.py`)
- Routes all database operations to the correct tenant database
- Uses thread-local storage to track the current tenant database
- `set_tenant_db(organization_id)` - Sets the active database
- `get_tenant_db()` - Retrieves the active database name

### 2. Enhanced Middleware (`saas/middleware.py`)
- Detects the organization from the request URL (domain/subdomain)
- Automatically activates the tenant database for that organization
- Thread-safe database switching using `set_tenant_db()`
- Clears the tenant context after request completes

### 3. Multi-Database Configuration (`settings.py`)
```python
DATABASES = {
    'default': {
        # System database for SaaS infrastructure
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
    # Tenant databases are added dynamically:
    # 'tenant_1': {...},
    # 'tenant_2': {...},
    # etc.
}

DATABASE_ROUTERS = ['saas.db_router.TenantDatabaseRouter']

# Function to add new tenant databases
add_tenant_database(organization_id, organization_slug)
```

### 4. Tenant Dashboard Views (`saas/tenant_dashboard_views.py`)

#### Available Views:
- **`tenant_dashboard`** - Main organization dashboard with statistics
- **`tenant_settings`** - Organization settings and configuration
- **`tenant_users`** - User management for the organization
- **`tenant_subscription`** - Subscription management and plan selection
- **`organization_switcher`** - (Admin only) Switch between organizations

#### URLs:
```
/tenant/dashboard/              - Organization dashboard
/tenant/settings/               - Organization settings
/tenant/users/                  - User management
/tenant/subscription/           - Subscription management
/tenant/organization-switcher/  - Organization switcher (superuser only)
/tenant/switch-organization/    - Switch organization (superuser only)
```

## How It Works

### Request Flow:
```
1. User request arrives (e.g., http://sos-school.local/tenant/dashboard/)
2. TenantMiddleware intercepts request
3. Middleware resolves organization from domain using resolve_organization_from_request()
4. Middleware sets request.organization = Organization instance
5. Middleware calls set_tenant_db(organization.id)
6. Database router routes ALL subsequent queries to tenant_N database
7. View executes and accesses organization-specific data
8. Middleware clears database context after response
```

### Database File Structure:
```
project_root/
├── db.sqlite3                    # System database (organizations, subscriptions, etc.)
└── tenant_databases/
    ├── db_sos-school.sqlite3     # Sos Herman Gmeiner School data
    ├── db_other-school.sqlite3   # Other School data
    └── ... (one database per organization)
```

## Usage Guide

### 1. Create a New Organization

Via Django Admin:
```
1. Go to /admin
2. Navigate to "Organizations"
3. Click "Add Organization"
4. Fill in: Name, Slug, Subdomain, is_active
5. Save
```

Or programmatically:
```python
from saas.models import Organization

org = Organization.objects.create(
    name='My School',
    slug='my-school',
    subdomain='my-school',
    is_active=True
)
```

### 2. Provision a Tenant Database

```bash
# Basic provisioning (creates database file)
python manage.py provision_tenant_database 1

# With migrations
python manage.py provision_tenant_database 1 --migrate

# With migrations and initial admin user
python manage.py provision_tenant_database 1 --migrate --create-admin
```

This command:
- Creates a new database file: `db_<slug>.sqlite3`
- Adds database to DATABASES configuration
- Optionally runs migrations on the new database
- Optionally creates initial admin user for the tenant

### 3. Access Organization Dashboard

1. **For the Organization:**
   - Access via domain: `http://sos-school.local/tenant/dashboard/`
   - Access via subdomain: `http://sos-school.localhost/tenant/dashboard/`

2. **URL Configuration:**
   - Each organization needs a domain or subdomain configured
   - Domain configuration can be done in Django Admin

3. **Admin User:**
   - Login with the admin user created during provisioning
   - Access `/tenant/dashboard/` to see organization statistics
   - Access `/tenant/users/` to manage users
   - Access `/tenant/settings/` for organization settings

### 4. Organization-Specific Database Access

All model queries automatically use the correct database:

```python
# In a view accessed via sos-school.local:
# This automatically queries tenant_1 database
from accounts.models import User
students = User.objects.filter(user_type='student')

# In a view accessed via other-school.local:
# This automatically queries tenant_2 database
students = User.objects.filter(user_type='student')

# Different databases, completely isolated!
```

## Configuration Examples

### Local Development Setup

Edit your `/etc/hosts` (Windows: `C:\Windows\System32\drivers\etc\hosts`):

```
127.0.0.1 sos-school.local
127.0.0.1 other-school.local
127.0.0.1 startup.local
```

Run the development server:
```bash
python manage.py runserver
```

Then access:
- `http://sos-school.local:8000/tenant/dashboard/` - Sos school dashboard
- `http://other-school.local:8000/tenant/dashboard/` - Other school dashboard

### Production Deployment

For production, configure proper domain names:

1. Register domain names (e.g., `sos-school.edu`, `other-school.edu`)
2. Point all school domains to the same server
3. Configure organization domains in Django Admin
4. Use the TenantMiddleware which detects organizations by domain

## Data Isolation Guarantees

### Complete Isolation:
- ✅ Separate database file for each organization
- ✅ No shared tables between organizations
- ✅ No cross-organization queries possible
- ✅ Each database has full schema (all models)

### Security:
- ✅ Users can only access their organization's data
- ✅ Admin users limited to their organization
- ✅ Superusers can access all organizations
- ✅ Automatic database routing prevents leakage

## Monitoring & Management

### View Active Organizations:
```python
from saas.models import Organization
organizations = Organization.objects.filter(is_active=True)
# Shows: name, slug, subscription status, number of users
```

### Check Database Files:
```bash
ls -la tenant_databases/
# Lists all tenant database files and their sizes
```

### Database Statistics:
```bash
du -h tenant_databases/db_*.sqlite3
# Shows size of each tenant database
```

## Advanced Features

### Multiple Domains per Organization

Organizations can have multiple domains:

```python
from saas.models import Organization, OrganizationDomain

org = Organization.objects.get(slug='sos-school')

# Add multiple domains
OrganizationDomain.objects.create(
    organization=org,
    domain='sos-school.edu',
    is_active=True
)

OrganizationDomain.objects.create(
    organization=org,
    domain='sos.school.edu',
    is_active=True
)
```

Both domains will route to the same organization dashboard.

### Superuser Access

Superusers can:
- Access `/tenant/organization-switcher/` to switch between organizations
- See data from all organizations
- Manage any organization

### Feature Flags per Plan

Each subscription plan has different features:

```python
subscription.plan.feature_flags = {
    'max_students': 500,
    'max_teachers': 20,
    'max_admins': 3,
    'features': {
        'attendance_tracking': True,
        'grade_management': True,
        'fee_management': True,      # Only in paid plans
        'advanced_reports': True,    # Only in paid plans
        'api_access': True,          # Enterprise only
    }
}
```

## Migration Instructions

If you're migrating from a shared database:

1. **Export data by organization** - Use management commands to export users/data per organization
2. **Create new organizations** - Create Organization records for each school
3. **Provision databases** - Run `provision_tenant_database` for each organization
4. **Import data** - Import data into each tenant database
5. **Assign organizations** - Ensure all users have organization_id set
6. **Test isolation** - Verify data is properly isolated per organization

## Troubleshooting

### Database Not Found Error

**Problem:** `django.db.utils.OperationalError: unable to open database file`

**Solution:**
```bash
# Make sure tenant_databases directory exists
mkdir -p tenant_databases

# Provision the database properly
python manage.py provision_tenant_database <org_id> --migrate
```

### Cross-Tenant Data Visible

**Problem:** Users from different organizations can see each other's data

**Solution:**
- Ensure TenantDatabaseRouter is in DATABASE_ROUTERS
- Verify TenantMiddleware is in MIDDLEWARE
- Check that organization.id matches tenant_N database name
- Run management command to fix orphaned users

### Migrations Not Running

**Problem:** `migrate` doesn't apply to tenant databases

**Solution:**
Use the provision command:
```bash
python manage.py provision_tenant_database <org_id> --migrate
```

Or manually:
```bash
python manage.py migrate --database=tenant_<id>
```

## Performance Considerations

### Advantages:
- ✅ Complete data isolation
- ✅ Each organization uses isolated database (no contention)
- ✅ Easy to backup individual organizations
- ✅ Easy to move organizations between servers
- ✅ Clear separation of concerns

### Considerations:
- ⚠️ More database files to manage
- ⚠️ Backups need to handle multiple files
- ⚠️ Migrations must be run per database

## Next Steps

1. ✅ Architecture implemented
2. ✅ Database routing configured
3. ✅ Tenant dashboard views created
4. ✅ Provisioning command created
5. → Test with real organizations
6. → Configure organization domains
7. → Create migration scripts for existing data
8. → Set up automated backups per tenant
