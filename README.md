# Django Allauth Multi-Tenant SSO

A Django-allauth extension that provides dynamic multi-tenant SSO support using OIDC and SAML.

## Features

- **Multi-Tenant Support**: Manage multiple organizations (tenants) with separate SSO configurations
- **OIDC & SAML**: Support for both OpenID Connect and SAML 2.0 protocols
- **Flexible Authentication**: Allow email/password OR SSO authentication per tenant
- **SSO Testing**: Tenant admins can test SSO configuration before enabling
- **User Invitations**: Invite users to tenants with role-based access
- **SSO Enforcement**: Optionally enforce SSO-only authentication for tenant users
- **Django-allauth Integration**: Seamlessly integrates with django-allauth

## Installation

Using uv:

```bash
uv pip install django-allauth-multitenant-sso
```

Using pip:

```bash
pip install django-allauth-multitenant-sso
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Multi-tenant SSO
    'django_allauth_multitenant_sso',
]
```

### 2. Configure Settings

```python
# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Django-allauth settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_ADAPTER = 'django_allauth_multitenant_sso.adapters.MultiTenantAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'django_allauth_multitenant_sso.adapters.MultiTenantSocialAccountAdapter'

# Multi-tenant SSO settings (optional)
MULTITENANT_ALLOW_OPEN_SIGNUP = False  # Require invitations
MULTITENANT_LOGIN_REDIRECT_URL = '/'
```

### 3. Add URLs

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('tenants/', include('django_allauth_multitenant_sso.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py migrate
```

## Usage

### Creating a Tenant

1. Access the Django admin
2. Create a new **Tenant** with a unique slug
3. Create a **TenantUser** record linking a user to the tenant with role "admin" or "owner"

### Configuring SSO

#### OIDC Configuration

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/`
2. Select OIDC protocol
3. Configure:
   - **Issuer URL**: Your OIDC provider's issuer (e.g., `https://accounts.google.com`)
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

#### SAML Configuration

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/`
2. Select SAML protocol
3. Configure:
   - **Entity ID**: SAML entity ID from your IdP
   - **SSO URL**: Single Sign-On URL from your IdP
   - **X.509 Certificate**: Identity provider's certificate (PEM format)
   - **Attribute Mapping**: JSON mapping of SAML attributes to user fields

**Supported SAML Providers:**
- Okta
- Azure AD
- OneLogin
- PingFederate
- Any SAML 2.0 compatible IdP

### Testing SSO

1. Navigate to `/tenants/tenant/<tenant-slug>/sso/test/`
2. Click "Test Configuration"
3. Review test results
4. If successful, enable SSO for the tenant

### Enabling SSO

1. Navigate to `/tenants/tenant/<tenant-slug>/`
2. Click "Enable SSO"
3. Optionally enforce SSO (disable password authentication)

### User Login Flow

**With SSO Enabled:**
- Users visit: `/tenants/sso/login/<tenant-slug>/`
- Redirected to SSO provider
- Authenticated and redirected back to your app

**Without SSO (or optional):**
- Users can still login via `/accounts/login/` with email/password

### Inviting Users

1. Navigate to `/tenants/tenant/<tenant-slug>/invite/`
2. Enter user email and select role
3. User receives invitation email with a unique link
4. User clicks the link to accept and join the tenant
5. Inviter receives a notification when invitation is accepted

## Models

### Tenant
- Represents an organization
- Can have multiple users and one SSO provider
- Fields: name, slug, domain, sso_enabled, sso_enforced

### TenantUser
- Links users to tenants
- Fields: user, tenant, role (member/admin/owner), external_id

### SSOProvider
- Stores SSO configuration per tenant
- Supports OIDC and SAML protocols
- Fields: protocol, OIDC settings, SAML settings, test results

### TenantInvitation
- Manages user invitations to tenants
- Fields: email, tenant, role, status, token, expires_at

## API Reference

### Adapters

**MultiTenantAccountAdapter**
- Custom django-allauth adapter
- Handles tenant-aware signup and login
- Enforces SSO when configured

**MultiTenantSocialAccountAdapter**
- Handles SSO provider authentication
- Links users to tenants via SSO

### Decorators

**@tenant_member_required**
- Ensures user is a member of the tenant
- Usage: `@tenant_member_required` on views

**@tenant_admin_required**
- Ensures user is admin/owner of tenant
- Usage: `@tenant_admin_required` on views

## Configuration Options

### Basic Settings

```python
# Allow users to signup without invitation
MULTITENANT_ALLOW_OPEN_SIGNUP = False

# Redirect URL after SSO login
MULTITENANT_LOGIN_REDIRECT_URL = '/'

# Redirect URL after connecting social account
MULTITENANT_ACCOUNT_CONNECT_REDIRECT_URL = '/accounts/connections/'
```

### Email Configuration

```python
# Site information (used in emails)
SITE_NAME = 'Your Platform Name'
SITE_DOMAIN = 'yourdomain.com'

# Email backend (for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email backend (for production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'

# Default from email
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

# Invitation email settings
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
MULTITENANT_INVITATION_REPLY_TO_INVITER = True  # Set reply-to as inviter's email
```

### Email Templates

The package includes default HTML and plain text email templates:

- `allauth_multitenant_sso/email/invitation_subject.txt`
- `allauth_multitenant_sso/email/invitation_message.txt`
- `allauth_multitenant_sso/email/invitation_message.html`

You can override these templates in your project's template directory.

## Management Commands

The package includes several management commands for managing invitations:

### Send Pending Invitations

Send or resend invitation emails:

```bash
# Send all pending invitations
python manage.py send_pending_invitations

# Send invitations for specific tenant
python manage.py send_pending_invitations --tenant-slug=acme

# Send invitation to specific email
python manage.py send_pending_invitations --email=user@example.com

# Dry run (show what would be sent without sending)
python manage.py send_pending_invitations --dry-run

# Resend all pending invitations
python manage.py send_pending_invitations --resend
```

### Cleanup Invitations

Clean up expired or old invitations:

```bash
# Mark expired invitations as expired
python manage.py cleanup_invitations

# Delete expired invitations
python manage.py cleanup_invitations --delete-expired

# Delete accepted invitations older than 30 days
python manage.py cleanup_invitations --delete-accepted --days=30

# Dry run
python manage.py cleanup_invitations --dry-run
```

### List Invitations

View all invitations:

```bash
# List all invitations
python manage.py list_invitations

# Filter by tenant
python manage.py list_invitations --tenant-slug=acme

# Filter by status
python manage.py list_invitations --status=pending

# Show only expired invitations
python manage.py list_invitations --expired

# Output as JSON
python manage.py list_invitations --format=json
```

## Example Project

See the `example/` directory for a complete working example.

```bash
cd example
uv pip install -e ..
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Requirements

- Python 3.10+
- Django 4.2+
- django-allauth 0.57.0+
- python3-saml 1.15.0+
- authlib 1.3.0+
- cryptography 41.0.0+

## Architecture

### Authentication Flow

1. User attempts login
2. System checks if user's tenant has SSO enabled
3. If SSO enforced, redirects to SSO provider
4. If SSO optional, shows choice of password or SSO
5. After SSO authentication, user is logged in and linked to tenant

### Multi-Tenant Isolation

- Each tenant has independent SSO configuration
- Users can belong to multiple tenants
- Tenant context stored in session
- Role-based access control per tenant

## Security Considerations

- Always use HTTPS in production
- Protect client secrets and certificates
- Validate SAML signatures
- Use CSRF protection
- Implement rate limiting on authentication endpoints
- Regularly rotate SSO credentials

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Additional Documentation

- [Email Configuration Guide](EMAIL_CONFIGURATION.md) - Detailed email setup for various providers
- [Architecture Documentation](ARCHITECTURE.md) - Technical architecture and design decisions
- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes

## Support

- GitHub Issues: https://github.com/yourusername/django-allauth-multitenant-sso/issues
- Documentation: https://github.com/yourusername/django-allauth-multitenant-sso#readme

## Changelog

### 0.1.0 (Initial Release)

- Multi-tenant support
- OIDC provider integration
- SAML provider integration
- SSO testing functionality
- User invitation system with email notifications
- Customizable HTML and plain text email templates
- Invitation acceptance notifications
- Management commands for invitation management
- Django admin integration
- Example project

## Credits

Built with:
- [django-allauth](https://github.com/pennersr/django-allauth)
- [python3-saml](https://github.com/onelogin/python3-saml)
- [Authlib](https://github.com/lepture/authlib)