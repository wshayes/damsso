# Django Allauth Multi-Tenant SSO

A Django-allauth extension that provides dynamic multi-tenant SSO support using OIDC and SAML.

## Features

- **Multi-Tenant Support**: Manage multiple organizations (tenants) with separate SSO configurations
- **OIDC & SAML**: Support for both OpenID Connect and SAML 2.0 protocols
- **Flexible Authentication**: Allow email/password OR SSO authentication per tenant
- **SSO Testing**: Tenant admins can test SSO configuration before enabling
- **User Invitations**: Invite users to tenants with role-based access
- **SSO Enforcement**: Optionally enforce SSO-only authentication for tenant users
- **Tenant-Specific Signup**: Public signup URLs with randomized tokens for each tenant
- **Django-allauth Integration**: Seamlessly integrates with django-allauth
- **Email-Only Authentication**: Uses email addresses as usernames (no separate username field)

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
uv pip install django-allauth-multitenant-sso
```

**Note:** While pip may work, this project is developed and tested with uv. For development, uv is required.

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

# Django-allauth settings (email-only authentication)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
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

## Documentation

Comprehensive documentation is available:

- **Online**: https://wshayes.github.io/django-allauth-multitenant-sso/
- **Local**: See the [`docs/`](docs/) folder

### Building Documentation Locally

```bash
# Start development server (with live reload)
just docs-dev

# Build static site
just docs-build

# Publish to GitHub Pages
just docs-publish
```

- **[Quick Start Guide](docs/quickstart.md)** - Get up and running in 5 minutes
- **[Usage Guide](docs/usage.md)** - How to use the package (creating tenants, configuring SSO, inviting users)
- **[Configuration Guide](docs/configuration.md)** - All configuration options
- **[Models Reference](docs/models.md)** - Data models and their fields
- **[API Reference](docs/api-reference.md)** - Programmatic API (adapters, decorators, views)
- **[Management Commands](docs/management-commands.md)** - Command-line tools
- **[Architecture Documentation](docs/architecture.md)** - Technical architecture and design decisions
- **[Email Configuration Guide](docs/email-configuration.md)** - Email setup for various providers

## Example Project

See the `example/` directory for a complete working example.

### Quick Setup with Just

```bash
# Setup the example demo site
just example-setup

# Create a superuser
just example-createsuperuser

# Start the development server
just dev
```

### Manual Setup

```bash
cd example
uv pip install -e ..
uv pip install django django-allauth python3-saml authlib cryptography
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

## Development

### Using Just (Recommended)

This project includes a `justfile` for common development tasks. [Install just](https://github.com/casey/just) and then:

```bash
# Setup development environment
just setup

# Run tests
just test

# Run tests with coverage
just test-cov

# Format code
just format

# Lint code
just lint

# Run all checks
just check

# Build package
just build

# See all available commands
just --list
```

### Manual Setup

```bash
# Install dependencies
uv pip install -e ".[test]"

# Install pre-commit hooks
uv pip install pre-commit
pre-commit install

# Run tests
pytest tests/ -v
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see LICENSE file for details

## Additional Resources

- [Contributing Guide](CONTRIBUTING.md) - Guidelines for contributing to the project
- [Security Policy](SECURITY.md) - How to report security vulnerabilities
- [Changelog](CHANGELOG.md) - Version history and changes
- [Agent Guidelines](AGENTS.md) - Guidelines for AI agents and automated tools (uses uv exclusively)

## Support

- GitHub Issues: https://github.com/wshayes/django-allauth-multitenant-sso/issues
- Documentation: [docs/](docs/)
