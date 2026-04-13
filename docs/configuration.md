# Configuration Guide

This guide covers all configuration options for damsso.

## Basic Settings

### Required Settings

```python
# INSTALLED_APPS
INSTALLED_APPS = [
    # ... Django apps ...
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'damsso',
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Django-allauth adapters
ACCOUNT_ADAPTER = 'damsso.adapters.MultiTenantAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'damsso.adapters.MultiTenantSocialAccountAdapter'

# Email-only authentication
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
```

### Multi-Tenant SSO Settings

```python
# Allow users to signup without invitation
MULTITENANT_ALLOW_OPEN_SIGNUP = False  # Default: False

# Redirect URL after SSO login
MULTITENANT_LOGIN_REDIRECT_URL = '/'  # Default: '/'

# Redirect URL after connecting social account
MULTITENANT_ACCOUNT_CONNECT_REDIRECT_URL = '/accounts/connections/'  # Default: '/accounts/connections/'
```

## Email Configuration

### Development Setup

For development, use the console email backend to print emails to the terminal:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@example.com'
```

### Production Setup

See the [Email Configuration Guide](email-configuration.md) for detailed setup instructions for:
- Gmail (SMTP)
- SendGrid
- Amazon SES
- Mailgun
- Postmark

### Email Settings

```python
# Site information (used in emails)
SITE_NAME = 'Your Platform Name'
SITE_DOMAIN = 'yourdomain.com'

# Default from email
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

# Invitation email settings
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
MULTITENANT_INVITATION_REPLY_TO_INVITER = True  # Set reply-to as inviter's email
```

## Django-allauth Settings

### Authentication Method

```python
# Email-only authentication (recommended)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
```

### Email Verification

```python
# Email verification settings
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 'mandatory', 'optional', or 'none'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True
```

### Session Settings

```python
# Session configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = True  # HTTPS only (production)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

## SSO Configuration

### OIDC Settings

OIDC configuration is done per-tenant via the admin interface or tenant dashboard. No global settings required.

### SAML Settings

SAML configuration is done per-tenant via the admin interface or tenant dashboard. No global settings required.

### SSO Security

```python
# CSRF protection (enabled by default)
CSRF_COOKIE_SECURE = True  # HTTPS only (production)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

### Optional integration hooks

```python
# Outbound OIDC HTTP timeout in seconds (metadata, JWKS, token exchange, userinfo)
DAMSSO_OIDC_HTTP_TIMEOUT = 15

# Dotted path: callable (request, tenant, email, userinfo) -> None; raise ValueError to deny login
DAMSSO_SSO_USER_POLICY = None

# Dotted path: callable (request, user, tenant, sso_provider) -> None; run after TenantUser sync
DAMSSO_POST_SSO_USER = None
```

### Admin and ``DAMSSO_TENANT_MODEL``

When ``DAMSSO_TENANT_MODEL`` points at your own tenant model, damsso **does not**
register the bundled ``damsso.Tenant`` in the Django admin (that placeholder would
target a separate table). Register your tenant model yourself. damsso still registers
``TenantUser``, ``SSOProvider``, and ``TenantInvitation`` unless your project unregisters
them for UX reasons.

## Custom Templates

### Override Email Templates

Create your own templates in your project's `templates/` directory:

```
your_project/
└── templates/
    └── damsso/
        └── email/
            ├── invitation_subject.txt
            ├── invitation_message.txt
            └── invitation_message.html
```

### Override View Templates

```
your_project/
└── templates/
    └── damsso/
        ├── tenant_dashboard.html
        ├── manage_sso.html
        ├── test_sso.html
        └── ...
```

### Template Context

Available variables in email templates:
- `invitation` - The TenantInvitation object
- `tenant_name` - Name of the tenant
- `role` - Display name of the role (e.g., "Member")
- `invited_by_name` - Name of the person who sent the invitation
- `invited_by_email` - Email of the inviter
- `invitation_url` - Full URL to accept the invitation
- `expires_at` - Formatted expiration date
- `site_name` - Your site's name
- `domain` - Your site's domain

## Custom Adapters

### Custom Account Adapter

```python
# myapp/adapters.py
from damsso.adapters import MultiTenantAccountAdapter

class MyAccountAdapter(MultiTenantAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        # Add custom logic here
        user = super().save_user(request, user, form, commit)
        # ... your custom code ...
        return user
```

```python
# settings.py
ACCOUNT_ADAPTER = 'myapp.adapters.MyAccountAdapter'
```

### Custom Social Account Adapter

```python
# myapp/adapters.py
from damsso.adapters import MultiTenantSocialAccountAdapter

class MySocialAccountAdapter(MultiTenantSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Add custom logic here
        super().pre_social_login(request, sociallogin)
        # ... your custom code ...
```

```python
# settings.py
SOCIALACCOUNT_ADAPTER = 'myapp.adapters.MySocialAccountAdapter'
```

## Environment Variables

Store sensitive settings in environment variables:

```python
# settings.py
import os

# Email settings
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# SSO secrets (stored per-tenant in database, but you might have global settings)
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'localhost:8000')
SITE_NAME = os.environ.get('SITE_NAME', 'My Platform')
```

**`.env` file:**
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
SITE_DOMAIN=yourdomain.com
SITE_NAME=Your Platform Name
```

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use HTTPS for all URLs
- [ ] Set `SESSION_COOKIE_SECURE = True`
- [ ] Set `CSRF_COOKIE_SECURE = True`
- [ ] Configure production email backend
- [ ] Store secrets in environment variables
- [ ] Update redirect URIs in SSO providers
- [ ] Configure proper session storage (Redis recommended)
- [ ] Enable rate limiting on authentication endpoints
- [ ] Set up error monitoring
- [ ] Review security settings
- [ ] Test SSO with production IdP
- [ ] Create backup admin account

## Advanced Configuration

### Custom User Model

If you're using a custom user model:

```python
# settings.py
AUTH_USER_MODEL = 'myapp.CustomUser'

# Ensure your custom user model has an email field
# The package uses email for authentication
```

### Database Configuration

```python
# Use a production database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### Caching (Optional)

```python
# Redis cache for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# Cache session data
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Troubleshooting

### Settings Not Applied

1. Ensure settings are in the correct file (`settings.py`)
2. Restart the Django development server
3. Clear browser cache and cookies
4. Check for typos in setting names

### Email Not Sending

1. Check `EMAIL_BACKEND` is configured
2. Verify email credentials
3. Test with console backend first
4. Check Django logs for errors
5. See [Email Configuration Guide](email-configuration.md) for troubleshooting

### SSO Not Working

1. Verify SSO configuration in tenant dashboard
2. Test SSO configuration first
3. Check redirect URIs match exactly
4. Verify client ID and secret
5. Check Django logs for errors
6. Review [Usage Guide](usage.md) for SSO setup

## Next Steps

- Review the [Usage Guide](usage.md) for common workflows
- Check the [API Reference](api-reference.md) for programmatic access
- See the [Architecture Documentation](architecture.md) for technical details

