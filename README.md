# DAMSSO (Django Allauth Multitenant SSO)

A Django-allauth extension that provides dynamic multi-tenant SSO support using OIDC and SAML.

## Features

- **Multi-Tenant Support**: Manage multiple organizations (tenants) with separate SSO configurations
- **OIDC & SAML**: Support for both OpenID Connect and SAML 2.0 protocols
- **Flexible Authentication**: Allow email/password AND/OR SSO authentication per tenant
- **SSO Testing**: Tenant admins can test SSO configuration before enabling
- **User Invitations**: Invite users to tenants with role-based access
- **SSO Enforcement**: Optionally enforce SSO-only authentication for tenant users
- **Tenant-Specific Signup**: Public signup URLs with randomized tokens for each tenant
- **Django-allauth Integration**: Seamlessly integrates with django-allauth
- **Email-Only Authentication**: Uses email addresses as usernames (no separate username field)
- **Row Level Security (RLS)**: Database-level tenant isolation with PostgreSQL (optional)
- **UUID7 Primary Keys**: Time-ordered UUIDs for better database indexing performance
- **Field-Level Encryption**: Sensitive SSO credentials encrypted at rest in database

## Authentication Model

**⚠️ IMPORTANT**: This package implements **two separate authentication systems**:

### 1. Django Account Users (SaaS Application Management)
- **Purpose**: Administrative access to the Django application itself
- **Login URL**: `/admin/` or `/accounts/login/`
- **Use Cases**:
  - Django superusers who manage the platform
  - Staff users who need access to the Django admin interface
  - Creating and managing tenants via Django admin
- **Managed Via**: Django's built-in `User` model and admin interface

### 2. Tenant Users (Tenant-Specific Authentication)
- **Purpose**: Users who belong to specific tenants/organizations
- **Login URL**: `/tenants/login/<tenant-slug>/`
- **Use Cases**:
  - Organization members who access tenant-specific features
  - SSO-authenticated users from external identity providers
  - Email/password authentication for tenant members
- **Managed Via**: `TenantUser` model linking users to tenants with roles

### Key Differences

| Aspect         | Django Account Users    | Tenant Users                                      |
| -------------- | ----------------------- | ------------------------------------------------- |
| Authentication | Django admin login      | Tenant-specific login at `/tenants/login/<slug>/` |
| Purpose        | Platform administration | Tenant membership and access                      |
| SSO Support    | No (uses Django auth)   | Yes (OIDC/SAML per tenant)                        |
| Multi-tenancy  | N/A                     | Users can belong to multiple tenants              |
| Roles          | Staff/Superuser         | Member/Admin/Owner per tenant                     |
| Model          | Django `User`           | `TenantUser` (links User to Tenant)               |

**Note**: A single Django `User` can be both a platform administrator AND a member of one or more tenants. The authentication flows are completely separate.

## Tenant Data Isolation

This package provides **two layers of tenant data isolation**:

### 1. Application-Level Isolation (Default)
- Works with any database (SQLite, PostgreSQL, MySQL, etc.)
- Uses Django QuerySets to filter data by tenant
- Session-based tenant context (`current_tenant_id` in session)
- Decorators enforce tenant membership (`@tenant_member_required`, `@tenant_admin_required`)

### 2. Database-Level Isolation with Row Level Security (Optional)
- **Requires PostgreSQL** and `django-rls` package
- Provides an additional security layer at the database level
- Automatically filters all queries to only show current tenant's data
- Prevents accidental data leaks even if application logic fails
- Recommended for production deployments

**When to use RLS:**
- Production environments with strict security requirements
- Multi-tenant SaaS applications with sensitive data
- Compliance requirements (HIPAA, SOC 2, etc.)
- When you want defense-in-depth security

**How it works:**
1. Middleware sets the current tenant ID in the database session
2. PostgreSQL RLS policies automatically filter all queries
3. One tenant cannot see or modify another tenant's data
4. Works transparently - no application code changes needed

See the [RLS Setup Guide](docs/rls-setup.md) for configuration details.

## Field-Level Encryption

Sensitive SSO provider credentials are **automatically encrypted at rest** in the database:

### Encrypted Fields
- **OIDC Client Secrets**: OAuth client secrets are encrypted before storage
- **SAML X.509 Certificates**: SAML signing certificates are encrypted

### How It Works
- Uses **Fernet symmetric encryption** (AES 128-bit in CBC mode)
- Encryption happens automatically when saving to database
- Decryption happens automatically when reading from database
- Transparent to application code - access fields normally

### Security Benefits
- **Database dump protection**: Leaked database dumps don't expose secrets
- **Compliance**: Meets requirements for PCI-DSS, HIPAA, SOC 2
- **Defense in depth**: Additional security layer beyond database permissions
- **Key rotation**: Supports multiple encryption keys for zero-downtime rotation

### Configuration Required

```python
# settings.py
from cryptography.fernet import Fernet

# Generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEYS = [
    'your-generated-encryption-key-here',
    # Optional: add old keys here for key rotation
]
```

**⚠️ CRITICAL**:
- Keep encryption keys secure (environment variables, secrets manager)
- Losing encryption keys means losing access to encrypted data
- Back up encryption keys separately from database backups

See the [Security Guide](docs/security.md) for key management best practices.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
uv pip install damsso
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
    'damsso',
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
ACCOUNT_ADAPTER = 'damsso.adapters.MultiTenantAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'damsso.adapters.MultiTenantSocialAccountAdapter'

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
    path('tenants/', include('damsso.urls')),
]
```

### 4. Run Migrations

```bash
python manage.py migrate
```

## Documentation

Comprehensive documentation is available:

- **Online**: https://wshayes.github.io/damsso/
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

## Docker Demo Environment (Recommended)

The fastest way to see everything working end-to-end. Starts Django, Keycloak (OIDC + SAML identity provider), PostgreSQL, and Mailpit with a single command:

```bash
just docker-up
```

This gives you three pre-configured tenants with working SSO:

| Tenant | URL | SSO | Test Users (password: `password`) |
|--------|-----|-----|------------|
| Acme Corp | http://localhost:8000/tenants/login/acme-oidc/ | OIDC | alice@acme.com, bob@acme.com |
| Globex Corp | http://localhost:8000/tenants/login/globex-saml/ | SAML 2.0 | carol@globex.com, dave@globex.com |
| Initech | http://localhost:8000/tenants/login/initech/ | None | nouser@initech.com |

**Django admin:** admin@demo.com / demo | **Keycloak:** http://localhost:8443 (admin / admin) | **Mailpit:** http://localhost:8025

See the [Docker Demo README](docker/README.md) for full details, testing flows, and troubleshooting.

## Example Project

See the `example/` directory for a standalone example (without Docker/Keycloak).

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
- cryptography 41.0.0+ (for field-level encryption using Fernet)
- uuid-utils 0.9.0+ (for UUID7 primary keys)
- django-rls 1.0.0+ (optional, for PostgreSQL Row Level Security)
- psycopg2-binary (optional, for PostgreSQL support)

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

- GitHub Issues: https://github.com/wshayes/damsso/issues
- Documentation: [docs/](docs/)
