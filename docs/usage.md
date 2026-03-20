# Usage Guide

This guide explains how to use damsso in your Django project.

## Creating a Tenant

### Via Django Admin

1. Access the Django admin at `/admin/`
2. Navigate to **Multi-Tenant SSO** → **Tenants**
3. Click **Add Tenant**
4. Fill in:
   - **Name**: Display name (e.g., "Acme Corporation")
   - **Slug**: URL-friendly identifier (e.g., "acme")
   - **Domain**: Optional domain for the tenant
   - **Is Active**: Check to enable the tenant
5. Click **Save**
6. Create a **TenantUser** record:
   - Navigate to **Multi-Tenant SSO** → **Tenant Users**
   - Click **Add Tenant User**
   - Select your user and the tenant
   - Set **Role** to "admin" or "owner"
   - Check **Is Active**
   - Click **Save**

### Via Django Shell

```python
from django.contrib.auth import get_user_model
from damsso.models import Tenant, TenantUser

User = get_user_model()

# Create tenant
tenant = Tenant.objects.create(
    name="Acme Corporation",
    slug="acme",
    domain="acme.com",
    is_active=True
)

# Link admin user
user = User.objects.get(email="admin@example.com")
TenantUser.objects.create(
    user=user,
    tenant=tenant,
    role="owner",
    is_active=True
)
```

## Configuring SSO

### OIDC Configuration

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/` (you must be a tenant admin)
2. Select **OIDC** protocol
3. Configure the following fields:
   - **Name**: Display name for the provider (e.g., "Google Workspace")
   - **Issuer URL**: Your OIDC provider's issuer URL
     - Google: `https://accounts.google.com`
     - Microsoft: `https://login.microsoftonline.com/{tenant-id}/v2.0`
     - Okta: `https://{your-domain}.okta.com`
     - Auth0: `https://{your-domain}.auth0.com`
   - **Client ID**: OAuth client ID from your provider
   - **Client Secret**: OAuth client secret
   - **Scopes**: Space-separated scopes (default: `openid email profile`)

**Supported OIDC Providers:**
- Google Workspace
- Microsoft Azure AD / Entra ID
- Okta
- Auth0
- Keycloak
- Any OpenID Connect compatible provider

**Note:** Make sure to register the callback URL in your OIDC provider:
- `http://localhost:8000/tenants/sso/oidc/callback/<tenant-slug>/` (development)
- `https://yourdomain.com/tenants/sso/oidc/callback/<tenant-slug>/` (production)

### SAML Configuration

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/`
2. Select **SAML** protocol
3. First, download your tenant's SP metadata:
   - Visit `/tenants/sso/saml/metadata/<tenant-id>/`
   - Copy the metadata XML
4. Configure your IdP (Identity Provider):
   - Upload the SP metadata to your IdP, OR
   - Manually configure:
     - **ACS URL**: `http://localhost:8000/tenants/sso/saml/acs/<tenant-id>/`
     - **Entity ID**: (from SP metadata)
5. Fill in the SAML form:
   - **Name**: Display name (e.g., "Okta SAML")
   - **Entity ID**: SAML entity ID from your IdP
   - **SSO URL**: Single Sign-On URL from your IdP
   - **X.509 Certificate**: Identity provider's certificate (PEM format, no headers)
   - **Attribute Mapping**: JSON mapping of SAML attributes to user fields
     ```json
     {
       "email": "email",
       "firstName": "first_name",
       "lastName": "last_name"
     }
     ```

**Supported SAML Providers:**
- Okta
- Azure AD
- OneLogin
- PingFederate
- Any SAML 2.0 compatible IdP

## Testing SSO

Before enabling SSO, you should test the configuration:

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/test/`
2. Click **Test Configuration**
3. Review the test results:
   - **OIDC**: Checks issuer reachability, endpoint discovery, and credentials
   - **SAML**: Validates entity ID, SSO URL, certificate format, and metadata
4. If successful, you'll see a success message
5. If there are errors, review the error messages and fix the configuration

**Important:** SSO can only be enabled after a successful test.

## Enabling SSO

Once SSO is configured and tested:

1. Navigate to `/tenants/tenant/<tenant-slug>/` (tenant dashboard)
2. Click **Enable SSO**
3. Optionally check **Enforce SSO** to disable password authentication for tenant users

### SSO Modes

**Optional SSO** (`sso_enabled=True`, `sso_enforced=False`):
- Users can choose between password login and SSO
- Password login: `/accounts/login/`
- SSO login: `/tenants/sso/login/<tenant-slug>/`

**Enforced SSO** (`sso_enabled=True`, `sso_enforced=True`):
- Password login is blocked for tenant users
- Users must use SSO: `/tenants/sso/login/<tenant-slug>/`

## User Login Flow

### With SSO Enabled

1. User visits: `/tenants/sso/login/<tenant-slug>/`
2. System redirects to the SSO provider
3. User authenticates at the IdP
4. IdP redirects back to your application
5. System creates/updates user and TenantUser records
6. User is logged in and redirected to the dashboard

### Without SSO (or Optional)

Users can still login via `/accounts/login/` with email/password.

### SSO Enforcement

If SSO is enforced for a tenant:
- Users with active TenantUser records for that tenant will be redirected to SSO
- Password authentication is blocked for those users
- Users without tenant membership can still use password login

## Inviting Users

### Via Tenant Dashboard

1. Navigate to `/tenants/tenant/<tenant-slug>/invite/` (as tenant admin)
2. Enter:
   - **Email**: User's email address
   - **Role**: member, admin, or owner
3. Click **Send Invitation**
4. User receives an invitation email with a unique link
5. User clicks the link to accept and join the tenant
6. Inviter receives a notification when the invitation is accepted

### Via Django Shell

```python
from damsso.models import TenantInvitation
from damsso.emails import send_invitation_email

invitation = TenantInvitation.objects.create(
    tenant=tenant,
    email="user@example.com",
    role="member",
    invited_by=admin_user
)

# Send invitation email
send_invitation_email(invitation)

# Get invitation URL (if needed)
invitation_url = f"http://localhost:8000/tenants/invitation/{invitation.token}/accept/"
```

### Invitation Status

Invitations have the following statuses:
- **pending**: Waiting for user to accept
- **accepted**: User has joined the tenant
- **expired**: Invitation has expired
- **cancelled**: Invitation was cancelled

## Tenant-Specific Signup URLs

Each tenant can have a public signup URL with a randomized token:

1. Navigate to `/tenants/tenant/<tenant-slug>/` (as tenant admin)
2. In the **Signup URL** section:
   - Click **Generate Token** to create a new signup URL
   - Copy the URL to share with users
   - Click **Clear Token** to disable the signup URL
3. Users visiting the signup URL will:
   - Be redirected to the signup page if not logged in
   - Automatically join the tenant after signing up
   - If already logged in, be added to the tenant immediately

### Via Django Admin

1. Navigate to **Multi-Tenant SSO** → **Tenants**
2. In the tenants list view:
   - Select the checkbox next to the tenant(s) you want to generate tokens for
   - In the "Action" dropdown at the top, select **Generate/Reset signup token**
   - Click **Go**
3. Open the tenant to view the signup URL:
   - Click on the tenant name to open it
   - In the **Signup Settings** section, you'll see the signup URL
   - Copy the URL from the readonly input field
4. Share the URL with users who should join the tenant

**Note**: The signup token can only be generated via the admin action in the list view. There is no button in the individual tenant form.

## Multi-Tenant Membership

Users can belong to multiple tenants:

```python
# User exists in Tenant A and Tenant B
TenantUser.objects.create(user=user, tenant=tenant_a, role='member')
TenantUser.objects.create(user=user, tenant=tenant_b, role='admin')
```

The current tenant is stored in the session: `request.session['current_tenant_id']`

## Common Workflows

### Allow Both Password and SSO

```python
# In Django admin or via code:
tenant.sso_enabled = True
tenant.sso_enforced = False  # Users can choose
tenant.save()
```

Users can login via:
- Password: `/accounts/login/`
- SSO: `/tenants/sso/login/<tenant-slug>/`

### Enforce SSO Only

```python
tenant.sso_enabled = True
tenant.sso_enforced = True  # SSO required
tenant.save()
```

Password login will be blocked for tenant users.

### Switch Between Tenants

If a user belongs to multiple tenants, they can switch context:
- The current tenant is stored in the session
- Use `@tenant_member_required` decorator to ensure user is a member
- Access tenant via `request.tenant` in views

## Next Steps

- Read the [Configuration Guide](configuration.md) for advanced settings
- Review the [API Reference](api-reference.md) for programmatic access
- Check the [Architecture Documentation](architecture.md) for technical details

