# Row Level Security (RLS) Setup Guide

This guide explains how to enable database-level tenant isolation using PostgreSQL Row Level Security (RLS) with django-rls.

## Overview

Row Level Security (RLS) provides **database-level** tenant isolation as an additional security layer beyond application-level filtering. With RLS enabled:

- PostgreSQL automatically filters all queries to only show the current tenant's data
- One tenant cannot see or modify another tenant's data, even if application code has bugs
- All database operations (SELECT, INSERT, UPDATE, DELETE) are automatically scoped to the current tenant
- Provides defense-in-depth security for multi-tenant applications

## Requirements

- **PostgreSQL** 9.5 or later (RLS was introduced in PostgreSQL 9.5)
- **django-rls** package installed
- **psycopg2** or **psycopg2-binary** for PostgreSQL database adapter

## Installation

### 1. Install Dependencies

```bash
pip install django-rls psycopg2-binary
# or with uv
uv pip install django-rls psycopg2-binary
```

### 2. Configure PostgreSQL Database

Update your `settings.py` to use PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'multitenant_sso',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Add django-rls to INSTALLED_APPS

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Row Level Security (BEFORE other apps)
    'django_rls',

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Multi-tenant SSO
    'django_allauth_multitenant_sso',
]
```

**Important**: Add `django_rls` **before** `django_allauth_multitenant_sso` to ensure RLS policies are created correctly.

### 4. Add RLS Middleware

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',

    # Row Level Security middleware (AFTER AuthenticationMiddleware)
    'django_allauth_multitenant_sso.middleware.TenantRLSMiddleware',
]
```

**Important**: Add `TenantRLSMiddleware` **after** `AuthenticationMiddleware` to ensure the user session is available.

### 5. Run Migrations

```bash
python manage.py migrate
```

This will:
1. Create the database tables for your models
2. Run the RLS setup migration (`0003_setup_rls.py`) which:
   - Enables RLS on tenant-scoped tables
   - Creates RLS policies for `TenantUser`, `SSOProvider`, and `TenantInvitation` models
   - Configures PostgreSQL to filter queries by `tenant_id`

**Note**: The RLS migration automatically detects your database type and only runs on PostgreSQL. If you're using SQLite or another database, the migration will be skipped harmlessly.

## How It Works

### 1. Session Tenant Context

When a user logs in via tenant login (`/tenants/login/<tenant-slug>/`), the session stores the current tenant ID:

```python
# In tenant_login view
request.session['current_tenant_id'] = str(tenant.id)
request.session['current_tenant_slug'] = tenant.slug
```

### 2. Middleware Sets Database Context

The `TenantRLSMiddleware` reads the tenant ID from the session and sets it in the PostgreSQL session:

```python
# In TenantRLSMiddleware
from django_rls import set_tenant

tenant_id = request.session.get('current_tenant_id')
if tenant_id:
    set_tenant(tenant_id)
```

This executes:
```sql
SELECT set_config('rls.tenant_id', '<tenant-uuid>', false);
```

### 3. PostgreSQL RLS Policies Enforce Isolation

Django-rls automatically creates RLS policies on models configured with `rls_tenant_field`:

```sql
-- Example for TenantUser table
ALTER TABLE django_allauth_multitenant_sso_tenantuser ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON django_allauth_multitenant_sso_tenantuser
    USING (tenant_id = current_setting('rls.tenant_id')::uuid);
```

Now all queries are automatically filtered:

```python
# Application code
users = TenantUser.objects.all()

# Actual SQL executed (PostgreSQL adds WHERE clause automatically)
SELECT * FROM django_allauth_multitenant_sso_tenantuser
WHERE tenant_id = current_setting('rls.tenant_id')::uuid;
```

## Models with RLS

The following models have RLS enabled by the `0003_setup_rls` migration:

| Model | RLS Field | Description | Policy Name |
|-------|-----------|-------------|-------------|
| `TenantUser` | `tenant_id` | User-to-tenant memberships | `django_allauth_multitenant_sso_tenantuser_tenant_isolation` |
| `SSOProvider` | `tenant_id` | SSO configuration per tenant | `django_allauth_multitenant_sso_ssoprovider_tenant_isolation` |
| `TenantInvitation` | `tenant_id` | User invitations per tenant | `django_allauth_multitenant_sso_tenantinvitation_tenant_isolation` |

The `Tenant` model itself does **not** have RLS enabled, as it represents the top-level organizational entity.

### RLS Policy Details

Each model has a PostgreSQL RLS policy that filters rows based on the current tenant:

```sql
-- Example policy for TenantUser
CREATE POLICY django_allauth_multitenant_sso_tenantuser_tenant_isolation
ON django_allauth_multitenant_sso_tenantuser
USING (
    tenant_id::text = current_setting('rls.tenant_id', true)
    OR current_setting('rls.tenant_id', true) IS NULL
);
```

This policy:
- **Filters by tenant**: Only shows rows where `tenant_id` matches the session's tenant
- **Allows admin access**: If no tenant is set (NULL), allows access to all rows
- **Applies to all operations**: Automatically applied to SELECT, INSERT, UPDATE, DELETE

## Admin Access

### Superuser Bypass

By default, PostgreSQL superusers bypass RLS policies. To ensure even superusers respect RLS:

```sql
ALTER TABLE django_allauth_multitenant_sso_tenantuser FORCE ROW LEVEL SECURITY;
ALTER TABLE django_allauth_multitenant_sso_ssoprovider FORCE ROW LEVEL SECURITY;
ALTER TABLE django_allauth_multitenant_sso_tenantinvitation FORCE ROW LEVEL SECURITY;
```

### Django Admin Access

Platform administrators using the Django admin interface (`/admin/`) do **not** have a tenant context set. This means:

- If RLS is strictly enforced, admins cannot see any tenant-specific data
- If you want admins to see all data, you need to either:
  1. Use a separate database user with BYPASSRLS privilege for admin operations
  2. Set a special tenant context for admins
  3. Temporarily disable RLS for admin views

**Recommended approach** for production:

```python
# settings.py
# Use separate database users for admin vs tenant access
DATABASES = {
    'default': {  # Tenant-scoped access
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'multitenant_sso',
        'USER': 'tenant_user',  # Has RLS enforced
        ...
    },
    'admin': {  # Admin access (optional)
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'multitenant_sso',
        'USER': 'admin_user',  # Has BYPASSRLS privilege
        ...
    },
}
```

## Testing RLS

### Verify RLS is Active

```python
from django.db import connection

# Check if RLS is enabled
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT tablename, rowsecurity
        FROM pg_tables
        WHERE tablename LIKE '%tenantuser%';
    """)
    print(cursor.fetchall())  # Should show rowsecurity = True
```

### Test Tenant Isolation

```python
from django_allauth_multitenant_sso.models import Tenant, TenantUser
from django_rls import set_tenant

# Create two tenants
tenant1 = Tenant.objects.create(name="Tenant 1", slug="tenant1")
tenant2 = Tenant.objects.create(name="Tenant 2", slug="tenant2")

# Create users for each tenant
user1 = TenantUser.objects.create(tenant=tenant1, ...)
user2 = TenantUser.objects.create(tenant=tenant2, ...)

# Set tenant context to tenant1
set_tenant(str(tenant1.id))

# Query should only return user1
users = TenantUser.objects.all()
print(users.count())  # Should be 1
print(users[0].tenant.name)  # Should be "Tenant 1"

# Switch to tenant2
set_tenant(str(tenant2.id))

# Query should only return user2
users = TenantUser.objects.all()
print(users.count())  # Should be 1
print(users[0].tenant.name)  # Should be "Tenant 2"
```

## Troubleshooting

### Issue: "relation does not exist" error

**Cause**: RLS policies were not created during migration.

**Solution**:
```bash
python manage.py migrate --run-syncdb
```

### Issue: Admin cannot see any data

**Cause**: RLS is enforced and no tenant context is set for admin users.

**Solution**: Set a tenant context in admin views or use BYPASSRLS privilege for admin database user.

### Issue: RLS policies not being applied

**Cause**: Middleware not installed or not in correct order.

**Solution**: Ensure `TenantRLSMiddleware` is in MIDDLEWARE list **after** `AuthenticationMiddleware`.

### Issue: "current_setting" function error

**Cause**: PostgreSQL session variable not set.

**Solution**: Ensure `set_tenant()` is called before database queries. Check middleware configuration.

## Performance Considerations

### Index Optimization

Create indexes on `tenant_id` fields for optimal performance:

```sql
CREATE INDEX idx_tenantuser_tenant ON django_allauth_multitenant_sso_tenantuser(tenant_id);
CREATE INDEX idx_ssoprovider_tenant ON django_allauth_multitenant_sso_ssoprovider(tenant_id);
CREATE INDEX idx_tenantinvitation_tenant ON django_allauth_multitenant_sso_tenantinvitation(tenant_id);
```

These indexes are automatically created by Django migrations.

### Query Performance

- RLS adds a WHERE clause to every query
- PostgreSQL optimizes RLS policies well
- Performance impact is minimal with proper indexing
- Monitor slow query log for optimization opportunities

## Security Best Practices

1. **Always Use RLS in Production**: Provides defense-in-depth security
2. **Test Isolation**: Verify tenants cannot access each other's data
3. **Monitor Logs**: Check PostgreSQL logs for RLS policy violations
4. **Regular Audits**: Periodically audit database access patterns
5. **Backup Strategy**: Ensure backups respect tenant boundaries
6. **Disaster Recovery**: Test tenant data restoration procedures

## Migration from SQLite to PostgreSQL

If you're currently using SQLite and want to migrate to PostgreSQL with RLS:

1. **Backup your SQLite database**:
   ```bash
   python manage.py dumpdata > backup.json
   ```

2. **Update settings.py** to use PostgreSQL (see step 2 above)

3. **Create PostgreSQL database**:
   ```bash
   createdb multitenant_sso
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Load data**:
   ```bash
   python manage.py loaddata backup.json
   ```

6. **Enable RLS** by following steps 3-5 above

## Additional Resources

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [django-rls Documentation](https://django-rls.com/)
- [Multi-Tenant Architecture Guide](architecture.md)
- [Security Best Practices](SECURITY.md)
