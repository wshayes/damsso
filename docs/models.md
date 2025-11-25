# Models Reference

This document describes all data models in django-allauth-multitenant-sso.

## Tenant

Represents an organization with its own SSO configuration.

### Fields

- **id** (UUID): Primary key
- **name** (CharField): Display name of the tenant
- **slug** (CharField): URL-friendly identifier (unique)
- **domain** (CharField, optional): Domain associated with the tenant
- **sso_enabled** (BooleanField): Whether SSO is enabled for this tenant
- **sso_enforced** (BooleanField): Whether SSO is required (password login disabled)
- **is_active** (BooleanField): Whether the tenant is active
- **signup_token** (CharField, optional): Randomized token for tenant-specific signup URLs
- **metadata** (JSONField, optional): Additional metadata
- **created_at** (DateTimeField): Creation timestamp
- **updated_at** (DateTimeField): Last update timestamp

### Relationships

- **tenant_users**: Related TenantUser objects (reverse relation)
- **sso_providers**: Related SSOProvider objects (reverse relation)
- **invitations**: Related TenantInvitation objects (reverse relation)

### Methods

- `get_active_sso_provider()`: Returns the active SSOProvider for this tenant
- `generate_signup_token()`: Generates a new randomized signup token
- `get_signup_url(request=None)`: Returns the full signup URL for this tenant

### Example

```python
from django_allauth_multitenant_sso.models import Tenant

# Create a tenant
tenant = Tenant.objects.create(
    name="Acme Corporation",
    slug="acme",
    domain="acme.com",
    is_active=True
)

# Generate signup URL
tenant.generate_signup_token()
signup_url = tenant.get_signup_url()

# Get active SSO provider
sso_provider = tenant.get_active_sso_provider()
```

## TenantUser

Links users to tenants with role-based access control.

### Fields

- **id** (UUID): Primary key
- **user** (ForeignKey): Reference to Django User model
- **tenant** (ForeignKey): Reference to Tenant model
- **role** (CharField): Role in the tenant (choices: 'member', 'admin', 'owner')
- **external_id** (CharField, optional): External SSO identity ID
- **is_active** (BooleanField): Whether the membership is active
- **created_at** (DateTimeField): Creation timestamp
- **updated_at** (DateTimeField): Last update timestamp

### Relationships

- **user**: Related User object
- **tenant**: Related Tenant object

### Methods

- `is_tenant_admin()`: Returns True if role is 'admin' or 'owner'
- `is_tenant_owner()`: Returns True if role is 'owner'

### Example

```python
from django_allauth_multitenant_sso.models import TenantUser

# Create tenant membership
tenant_user = TenantUser.objects.create(
    user=user,
    tenant=tenant,
    role='admin',
    is_active=True
)

# Check permissions
if tenant_user.is_tenant_admin():
    # User can manage SSO and invite users
    pass
```

## SSOProvider

Stores SSO configuration per tenant. Only one active provider per tenant.

### Fields

- **id** (UUID): Primary key
- **tenant** (ForeignKey): Reference to Tenant model
- **name** (CharField): Display name of the provider
- **protocol** (CharField): SSO protocol (choices: 'oidc', 'saml')
- **is_active** (BooleanField): Whether this provider is active
- **test_status** (CharField, optional): Last test status (choices: 'pending', 'success', 'failed')
- **test_results** (JSONField, optional): Detailed test results
- **tested_at** (DateTimeField, optional): Last test timestamp

### OIDC-Specific Fields

- **oidc_issuer_url** (CharField, optional): OIDC issuer URL
- **oidc_authorize_url** (CharField, optional): Authorization endpoint
- **oidc_token_url** (CharField, optional): Token endpoint
- **oidc_userinfo_url** (CharField, optional): UserInfo endpoint
- **oidc_client_id** (CharField): OAuth client ID
- **oidc_client_secret** (CharField): OAuth client secret
- **oidc_scopes** (CharField): Space-separated scopes (default: 'openid email profile')

### SAML-Specific Fields

- **saml_entity_id** (CharField, optional): SAML entity ID
- **saml_sso_url** (CharField, optional): Single Sign-On URL
- **saml_x509_cert** (TextField, optional): X.509 certificate (PEM format)
- **saml_attribute_mapping** (JSONField, optional): Attribute mapping JSON

### Relationships

- **tenant**: Related Tenant object

### Methods

- `get_provider_client()`: Returns an OIDCProviderClient or SAMLProviderClient instance

### Example

```python
from django_allauth_multitenant_sso.models import SSOProvider

# Create OIDC provider
oidc_provider = SSOProvider.objects.create(
    tenant=tenant,
    name="Google Workspace",
    protocol="oidc",
    oidc_issuer_url="https://accounts.google.com",
    oidc_client_id="your-client-id",
    oidc_client_secret="your-client-secret",
    oidc_scopes="openid email profile",
    is_active=True
)

# Create SAML provider
saml_provider = SSOProvider.objects.create(
    tenant=tenant,
    name="Okta SAML",
    protocol="saml",
    saml_entity_id="https://dev-123456.okta.com/app/abc123/sso/saml",
    saml_sso_url="https://dev-123456.okta.com/app/abc123/sso/saml",
    saml_x509_cert="-----BEGIN CERTIFICATE-----\n...",
    saml_attribute_mapping={"email": "email", "firstName": "first_name"},
    is_active=True
)
```

## TenantInvitation

Manages user invitations to tenants.

### Fields

- **id** (UUID): Primary key
- **tenant** (ForeignKey): Reference to Tenant model
- **email** (EmailField): Email address of the invited user
- **role** (CharField): Role to assign (choices: 'member', 'admin', 'owner')
- **status** (CharField): Invitation status (choices: 'pending', 'accepted', 'expired', 'cancelled')
- **token** (CharField): Unique invitation token
- **invited_by** (ForeignKey, optional): User who sent the invitation
- **expires_at** (DateTimeField): Expiration timestamp
- **accepted_at** (DateTimeField, optional): Acceptance timestamp
- **created_at** (DateTimeField): Creation timestamp
- **updated_at** (DateTimeField): Last update timestamp

### Relationships

- **tenant**: Related Tenant object
- **invited_by**: Related User object (who sent the invitation)

### Methods

- `is_valid()`: Returns True if invitation is pending and not expired
- `accept(user)`: Accepts the invitation and creates TenantUser membership
- `cancel()`: Cancels the invitation

### Example

```python
from django_allauth_multitenant_sso.models import TenantInvitation
from datetime import timedelta
from django.utils import timezone

# Create invitation
invitation = TenantInvitation.objects.create(
    tenant=tenant,
    email="user@example.com",
    role="member",
    invited_by=admin_user,
    expires_at=timezone.now() + timedelta(days=7)
)

# Check if valid
if invitation.is_valid():
    # Send invitation email
    pass

# Accept invitation
user = User.objects.get(email="user@example.com")
invitation.accept(user)
```

## Query Examples

### Get all tenants for a user

```python
from django_allauth_multitenant_sso.models import TenantUser

user_tenants = Tenant.objects.filter(
    tenant_users__user=user,
    tenant_users__is_active=True
).distinct()
```

### Get all users for a tenant

```python
from django.contrib.auth import get_user_model
from django_allauth_multitenant_sso.models import TenantUser

User = get_user_model()
tenant_users = User.objects.filter(
    tenant_users__tenant=tenant,
    tenant_users__is_active=True
).distinct()
```

### Get active SSO provider for tenant

```python
sso_provider = tenant.get_active_sso_provider()
if sso_provider:
    client = sso_provider.get_provider_client()
```

### Get pending invitations for a tenant

```python
pending_invitations = TenantInvitation.objects.filter(
    tenant=tenant,
    status='pending'
).filter(expires_at__gt=timezone.now())
```

### Get tenant admins

```python
admins = TenantUser.objects.filter(
    tenant=tenant,
    role__in=['admin', 'owner'],
    is_active=True
)
```

## Model Relationships Diagram

```
User
  └── TenantUser (many-to-many through TenantUser)
      └── Tenant
          ├── SSOProvider (one active per tenant)
          └── TenantInvitation
```

## Next Steps

- See the [Usage Guide](usage.md) for how to use these models
- Review the [API Reference](api-reference.md) for programmatic access
- Check the [Architecture Documentation](architecture.md) for design details

