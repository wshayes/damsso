# API Reference

This document provides detailed API reference for damsso.

## Adapters

### MultiTenantAccountAdapter

Custom django-allauth adapter that handles tenant-aware signup and login.

**Location:** `damsso.adapters.MultiTenantAccountAdapter`

**Base Class:** `allauth.account.adapter.DefaultAccountAdapter`

#### Methods

##### `is_open_for_signup(request)`

Determines if signup is allowed. Checks for tenant signup tokens or invitations.

**Parameters:**
- `request`: Django HttpRequest object

**Returns:** `bool`

**Example:**
```python
# Automatically called by django-allauth
# Checks request.session for 'tenant_signup_token' or 'invitation_token'
```

##### `save_user(request, user, form, commit=True)`

Saves a new user and creates tenant membership if applicable.

**Parameters:**
- `request`: Django HttpRequest object
- `user`: User instance
- `form`: Signup form
- `commit`: Whether to save to database (default: True)

**Returns:** User instance

**Example:**
```python
# Automatically called by django-allauth during signup
# Creates TenantUser if tenant_signup_token or invitation_token in session
```

##### `pre_authenticate(request, email, password, **kwargs)`

Called before authentication. Enforces SSO if required by tenant.

**Parameters:**
- `request`: Django HttpRequest object
- `email`: User email
- `password`: User password
- `**kwargs`: Additional keyword arguments

**Returns:** `None` or redirects to SSO

**Example:**
```python
# Automatically called by django-allauth
# Redirects to SSO if user's tenant has sso_enforced=True
```

##### `get_login_redirect_url(request)`

Returns the URL to redirect to after login.

**Parameters:**
- `request`: Django HttpRequest object

**Returns:** URL string

**Example:**
```python
# Uses MULTITENANT_LOGIN_REDIRECT_URL setting
```

### MultiTenantSocialAccountAdapter

Custom django-allauth adapter that handles SSO provider authentication.

**Location:** `damsso.adapters.MultiTenantSocialAccountAdapter`

**Base Class:** `allauth.socialaccount.adapter.DefaultSocialAccountAdapter`

#### Methods

##### `pre_social_login(request, sociallogin)`

Called before SSO login. Links user to tenant based on SSO context.

**Parameters:**
- `request`: Django HttpRequest object
- `sociallogin`: SocialLogin instance from django-allauth

**Returns:** `None`

**Example:**
```python
# Automatically called by django-allauth
# Checks for sso_tenant_id or invitation_token in session
# Creates/updates TenantUser membership
```

##### `save_user(request, sociallogin, form=None)`

Saves user after SSO authentication.

**Parameters:**
- `request`: Django HttpRequest object
- `sociallogin`: SocialLogin instance
- `form`: Optional form instance

**Returns:** User instance

**Example:**
```python
# Automatically called by django-allauth
# Creates TenantUser if tenant context is available
```

## Decorators

### @tenant_member_required

Ensures the user is an active member of the tenant.

**Location:** `damsso.decorators.tenant_member_required`

**Usage:**
```python
from damsso.decorators import tenant_member_required

@tenant_member_required
def my_view(request, tenant_slug):
    # User is guaranteed to be a member of the tenant
    tenant = request.tenant
    # ... your code ...
```

**Behavior:**
- Checks if user is authenticated
- Verifies user has active TenantUser membership for the tenant
- Sets `request.tenant` and `request.tenant_user` for use in the view
- Redirects to login if not authenticated
- Returns 403 if user is not a member

### @tenant_admin_required

Ensures the user is an admin or owner of the tenant.

**Location:** `damsso.decorators.tenant_admin_required`

**Usage:**
```python
from damsso.decorators import tenant_admin_required

@tenant_admin_required
def manage_sso(request, tenant_slug):
    # User is guaranteed to be an admin/owner
    tenant = request.tenant
    # ... your code ...
```

**Behavior:**
- Checks if user is authenticated
- Verifies user has active TenantUser membership with role 'admin' or 'owner'
- Sets `request.tenant` and `request.tenant_user` for use in the view
- Redirects to login if not authenticated
- Returns 403 if user is not an admin

## Views

### SSO Authentication Views

#### `sso_login(request, tenant_slug)`

Initiates SSO login for a tenant.

**URL Pattern:** `/tenants/sso/login/<tenant_slug>/`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Redirect to SSO provider

**Example:**
```python
# User visits: /tenants/sso/login/acme/
# Redirects to OIDC/SAML provider
```

#### `oidc_callback(request, tenant_slug)`

Handles OIDC callback after authentication.

**URL Pattern:** `/tenants/sso/oidc/callback/<tenant_slug>/`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Redirect to dashboard or login page

**Example:**
```python
# Called by OIDC provider after authentication
# Creates/updates user and TenantUser
# Logs user in
```

#### `saml_acs(request, tenant_id)`

SAML Assertion Consumer Service endpoint.

**URL Pattern:** `/tenants/sso/saml/acs/<tenant_id>/`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_id`: Tenant UUID

**Returns:** Redirect to dashboard or login page

**Example:**
```python
# Called by SAML IdP after authentication
# Validates SAML assertion
# Creates/updates user and TenantUser
# Logs user in
```

#### `saml_metadata(request, tenant_id)`

Generates SAML SP metadata for a tenant.

**URL Pattern:** `/tenants/sso/saml/metadata/<tenant_id>/`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_id`: Tenant UUID

**Returns:** XML metadata

**Example:**
```python
# Returns SAML SP metadata XML
# Used to configure IdP
```

### Tenant Management Views

#### `tenant_dashboard(request, tenant_slug)`

Tenant admin dashboard.

**URL Pattern:** `/tenants/tenant/<tenant_slug>/`

**Decorator:** `@login_required`, `@tenant_admin_required`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Rendered template

**Context:**
- `tenant`: Tenant instance
- `tenant_user`: TenantUser instance
- `member_count`: Number of active members
- `invitation_count`: Number of pending invitations
- `sso_provider`: Active SSOProvider (if any)

#### `manage_sso_provider(request, tenant_slug)`

Configure SSO provider for a tenant.

**URL Pattern:** `/tenants/tenant/<tenant_slug>/sso/`

**Decorator:** `@login_required`, `@tenant_admin_required`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Rendered template or redirect

**Methods:** GET (display form), POST (save configuration)

#### `test_sso_provider(request, tenant_slug)`

Test SSO provider configuration.

**URL Pattern:** `/tenants/tenant/<tenant_slug>/sso/test/`

**Decorator:** `@login_required`, `@tenant_admin_required`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Rendered template or redirect

**Methods:** GET (display test page), POST (run test)

#### `toggle_sso(request, tenant_slug)`

Enable/disable/enforce SSO for a tenant.

**URL Pattern:** `/tenants/tenant/<tenant_slug>/sso/toggle/`

**Decorator:** `@login_required`, `@tenant_admin_required`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Redirect

**Methods:** POST only

#### `invite_user(request, tenant_slug)`

Invite a user to a tenant.

**URL Pattern:** `/tenants/tenant/<tenant_slug>/invite/`

**Decorator:** `@login_required`, `@tenant_admin_required`

**Parameters:**
- `request`: Django HttpRequest object
- `tenant_slug`: Tenant slug

**Returns:** Rendered template or redirect

**Methods:** GET (display form), POST (send invitation)

#### `tenant_signup(request, token)`

Handle tenant-specific signup via a token.

**URL Pattern:** `/tenants/signup/<token>/`

**Parameters:**
- `request`: Django HttpRequest object
- `token`: Tenant signup token

**Returns:** Redirect to signup page or dashboard

**Example:**
```python
# User visits: /tenants/signup/abc123.../
# Token stored in session
# Redirects to signup page
# After signup, user automatically joins tenant
```

### Invitation Views

#### `accept_invitation(request, token)`

Accept a tenant invitation.

**URL Pattern:** `/tenants/invitation/<token>/accept/`

**Parameters:**
- `request`: Django HttpRequest object
- `token`: Invitation token

**Returns:** Redirect to signup page or dashboard

**Example:**
```python
# User clicks invitation link
# If not logged in, redirects to signup
# If logged in, creates TenantUser and redirects to dashboard
```

## Provider Clients

### OIDCProviderClient

Handles OpenID Connect authentication flow.

**Location:** `damsso.providers.OIDCProviderClient`

#### Methods

##### `get_authorization_url(request, redirect_uri)`

Generates OIDC authorization URL.

**Parameters:**
- `request`: Django HttpRequest object
- `redirect_uri`: Callback URL

**Returns:** Authorization URL string

##### `fetch_token(request, redirect_uri, code)`

Exchanges authorization code for access token.

**Parameters:**
- `request`: Django HttpRequest object
- `redirect_uri`: Callback URL
- `code`: Authorization code

**Returns:** Token dictionary

##### `get_userinfo(access_token)`

Retrieves user information from IdP.

**Parameters:**
- `access_token`: OAuth access token

**Returns:** User info dictionary

##### `test_connection()`

Tests OIDC configuration.

**Returns:** Tuple of (success: bool, results: dict)

### SAMLProviderClient

Handles SAML 2.0 authentication flow.

**Location:** `damsso.providers.SAMLProviderClient`

#### Methods

##### `get_saml_settings()`

Generates SAML configuration dictionary.

**Returns:** SAML settings dictionary

##### `test_connection()`

Tests SAML configuration.

**Returns:** Tuple of (success: bool, results: dict)

## Utilities

### Email Functions

#### `send_invitation_email(invitation, request=None)`

Sends an invitation email to a user.

**Location:** `damsso.emails.send_invitation_email`

**Parameters:**
- `invitation`: TenantInvitation instance
- `request`: Optional Django HttpRequest object (for building absolute URLs)

**Returns:** `None`

**Example:**
```python
from damsso.emails import send_invitation_email

invitation = TenantInvitation.objects.get(token=token)
send_invitation_email(invitation, request)
```

#### `send_invitation_accepted_notification(invitation, request=None)`

Sends a notification to the inviter when an invitation is accepted.

**Location:** `damsso.emails.send_invitation_accepted_notification`

**Parameters:**
- `invitation`: TenantInvitation instance
- `request`: Optional Django HttpRequest object

**Returns:** `None`

## Session Variables

The package uses the following session variables:

- `current_tenant_id`: UUID of the current tenant
- `tenant_signup_token`: Token for tenant-specific signup
- `invitation_token`: Token for invitation-based signup
- `sso_tenant_id`: Tenant ID during SSO flow

## Next Steps

- See the [Usage Guide](usage.md) for common workflows
- Review the [Models Reference](models.md) for data models
- Check the [Configuration Guide](configuration.md) for settings

