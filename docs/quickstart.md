# Quick Start Guide

Get up and running with django-allauth-multitenant-sso in 5 minutes.

## Installation

```bash
pip install django-allauth-multitenant-sso
# or
uv pip install django-allauth-multitenant-sso
```

## Basic Configuration

### 1. Update settings.py

```python
INSTALLED_APPS = [
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

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Sites framework
SITE_ID = 1

# Allauth settings
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_ADAPTER = 'django_allauth_multitenant_sso.adapters.MultiTenantAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'django_allauth_multitenant_sso.adapters.MultiTenantSocialAccountAdapter'

# Multi-tenant SSO settings
MULTITENANT_ALLOW_OPEN_SIGNUP = False

# Site configuration (for email links)
SITE_NAME = 'My Platform'
SITE_DOMAIN = 'localhost:8000'  # Change in production

# Email settings (console backend for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@example.com'
```

### 2. Update urls.py

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('tenants/', include('django_allauth_multitenant_sso.urls')),
]
```

### 3. Run migrations

```bash
python manage.py migrate
```

## Create Your First Tenant

### Via Django Admin

1. Create a superuser:
```bash
python manage.py createsuperuser
```

2. Start the dev server:
```bash
python manage.py runserver
```

3. Access admin at http://localhost:8000/admin/

4. Create a **Tenant**:
   - Name: "Acme Corporation"
   - Slug: "acme"
   - Is Active: ✓

5. Create a **Tenant User**:
   - User: (select your superuser)
   - Tenant: "Acme Corporation"
   - Role: "owner"
   - Is Active: ✓

### Via Django Shell

```python
from django.contrib.auth import get_user_model
from django_allauth_multitenant_sso.models import Tenant, TenantUser

User = get_user_model()

# Create tenant
tenant = Tenant.objects.create(
    name="Acme Corporation",
    slug="acme",
    domain="acme.com"
)

# Link admin user
user = User.objects.get(email="admin@example.com")
TenantUser.objects.create(
    user=user,
    tenant=tenant,
    role="owner"
)
```

## Configure SSO

### Option 1: OIDC (e.g., Google)

1. Set up OAuth credentials at https://console.cloud.google.com/
   - Create OAuth 2.0 Client ID
   - Add redirect URI: `http://localhost:8000/tenants/sso/oidc/callback/acme/`

2. Navigate to: http://localhost:8000/tenants/tenant/acme/sso/

3. Fill in the form:
   - Name: "Google Workspace"
   - Protocol: "OIDC"
   - Issuer: `https://accounts.google.com`
   - Client ID: (from Google Cloud Console)
   - Client Secret: (from Google Cloud Console)
   - Scopes: `openid email profile`

4. Click "Save"

5. Test the configuration:
   - Navigate to: http://localhost:8000/tenants/tenant/acme/sso/test/
   - Click "Test Configuration"
   - Verify success message

6. Enable SSO:
   - Navigate to: http://localhost:8000/tenants/tenant/acme/
   - Click "Enable SSO"

7. Test login:
   - Visit: http://localhost:8000/tenants/sso/login/acme/
   - Should redirect to Google login

### Option 2: SAML (e.g., Okta)

1. In Okta, create a new SAML app:
   - Download your tenant's SP metadata:
     `http://localhost:8000/tenants/sso/saml/metadata/<tenant-uuid>/`
   - Upload to Okta
   - Or manually configure:
     - ACS URL: `http://localhost:8000/tenants/sso/saml/acs/<tenant-uuid>/`
     - Entity ID: (from SP metadata)

2. Navigate to: http://localhost:8000/tenants/tenant/acme/sso/

3. Fill in the form:
   - Name: "Okta SAML"
   - Protocol: "SAML"
   - Entity ID: (from Okta app settings)
   - SSO URL: (from Okta app settings)
   - X.509 Certificate: (paste from Okta)
   - Attribute Mapping:
     ```json
     {
       "email": "email",
       "firstName": "first_name",
       "lastName": "last_name"
     }
     ```

4. Click "Save"

5. Test and enable (same as OIDC steps 5-7)

## Invite Users

### Via Admin Interface

1. Navigate to: http://localhost:8000/tenants/tenant/acme/invite/

2. Enter:
   - Email: user@example.com
   - Role: "member"

3. Click "Send Invitation"

4. User receives invitation link (currently logged to console)

5. User clicks link and signs up

### Via Code

```python
from django_allauth_multitenant_sso.models import TenantInvitation
from django_allauth_multitenant_sso.emails import send_invitation_email

invitation = TenantInvitation.objects.create(
    tenant=tenant,
    email="user@example.com",
    role="member",
    invited_by=admin_user
)

# Send invitation email
send_invitation_email(invitation)

# Get invitation URL (in case you need it)
invitation_url = f"http://localhost:8000/tenants/invitation/{invitation.token}/accept/"
```

### Email Notifications

The package automatically sends:
- **Invitation emails** to invited users with a secure link
- **Acceptance notifications** to inviters when users join

Email content is fully customizable by overriding the templates:
- `allauth_multitenant_sso/email/invitation_subject.txt`
- `allauth_multitenant_sso/email/invitation_message.txt`
- `allauth_multitenant_sso/email/invitation_message.html`

In development, emails are printed to the console. In production, configure a real email backend (see [Email Configuration Guide](email-configuration.md)).

## Common Workflows

### Allow Both Password and SSO

```python
# In Django admin, for your tenant:
tenant.sso_enabled = True
tenant.sso_enforced = False  # Users can choose
tenant.save()
```

Users can login via:
- Password: http://localhost:8000/accounts/login/
- SSO: http://localhost:8000/tenants/sso/login/acme/

### Enforce SSO Only

```python
tenant.sso_enabled = True
tenant.sso_enforced = True  # SSO required
tenant.save()
```

Password login will be blocked for tenant users.

### Multiple Tenants

Users can belong to multiple tenants:

```python
# User exists in Tenant A and Tenant B
TenantUser.objects.create(user=user, tenant=tenant_a, role='member')
TenantUser.objects.create(user=user, tenant=tenant_b, role='admin')
```

Current tenant stored in session: `request.session['current_tenant_id']`

## Testing SSO

### OIDC Test Checklist
- ✓ Issuer URL is reachable
- ✓ OpenID configuration is valid
- ✓ Client ID and secret are correct
- ✓ Redirect URI is whitelisted
- ✓ Scopes are supported

### SAML Test Checklist
- ✓ SP metadata is correct
- ✓ IdP can reach ACS URL
- ✓ Entity ID matches
- ✓ Certificate is valid
- ✓ Attribute mapping is correct

## Troubleshooting

### SSO Test Fails

**OIDC:**
- Check issuer URL is correct and reachable
- Verify client ID and secret
- Ensure redirect URI is registered in IdP

**SAML:**
- Verify certificate format (PEM, no headers)
- Check SSO URL is reachable
- Ensure SP metadata is uploaded to IdP

### User Not Created After SSO

- Check email is provided by IdP
- Verify attribute mapping (SAML)
- Check scopes include email (OIDC)
- Look for errors in Django logs

### SSO Enforced But Users Can Still Use Password

- Verify `tenant.sso_enforced = True`
- Check user has active TenantUser record
- Ensure tenant is active
- Clear user session

### Import Errors

```bash
# Ensure django-allauth is installed
pip install django-allauth

# Ensure middleware is configured
# Add 'allauth.account.middleware.AccountMiddleware' to MIDDLEWARE
```

## Next Steps

- Read the full [README](https://github.com/wshayes/django-allauth-multitenant-sso/blob/main/README.md)
- Review [Architecture documentation](architecture.md)
- Check out the [example project](https://github.com/wshayes/django-allauth-multitenant-sso/tree/main/example/)
- Customize templates for your app
- Set up email notifications for invitations
- Configure production SSO providers

## Production Checklist

Before deploying to production:

- [ ] Use HTTPS for all URLs
- [ ] Update redirect URIs in SSO providers
- [ ] Store secrets in environment variables
- [ ] Enable email backend for invitations
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use production database
- [ ] Set up error monitoring
- [ ] Configure session storage (Redis)
- [ ] Enable rate limiting
- [ ] Review security settings
- [ ] Test SSO with production IdP
- [ ] Create backup admin account
- [ ] Document tenant setup process

## Support

- Documentation: [README](https://github.com/wshayes/django-allauth-multitenant-sso/blob/main/README.md)
- Issues: https://github.com/wshayes/django-allauth-multitenant-sso/issues
- Examples: [example/](https://github.com/wshayes/django-allauth-multitenant-sso/tree/main/example/)
