# Django Allauth Multi-Tenant SSO - Architecture

## Overview

This package extends django-allauth to provide dynamic, per-tenant SSO configuration using OIDC and SAML protocols. Each tenant can have its own SSO provider, and users can belong to multiple tenants.

## Authentication Model

### Two Separate Authentication Systems

This package implements **two distinct authentication systems** that operate independently:

#### 1. Django Account Users (Platform Administration)

**Purpose**: Administrative access to the Django application and platform management.

- **Authentication Flow**: Standard Django authentication via `/admin/` or `/accounts/login/`
- **User Model**: Django's built-in `User` model
- **Use Cases**:
  - Django superusers managing the entire platform
  - Staff users with access to Django admin interface
  - Platform administrators creating and configuring tenants
  - Managing global SSO settings
- **Management**: Via Django admin interface (`/admin/`)
- **SSO**: Not supported (uses standard Django authentication)
- **Session Storage**: Django session with user ID

#### 2. Tenant Users (Tenant-Specific Access)

**Purpose**: Users who belong to specific tenants/organizations.

- **Authentication Flow**: Tenant-specific login at `/tenants/login/<tenant-slug>/`
- **User Model**: `TenantUser` model (links Django `User` to `Tenant`)
- **Use Cases**:
  - Organization members accessing tenant-specific features
  - SSO-authenticated users from external IdPs (Okta, Azure AD, etc.)
  - Email/password authentication for tenant members
  - Multi-tenant membership (one user in multiple organizations)
- **Management**: Via `TenantUser` model and tenant admin dashboard
- **SSO**: Full support for OIDC and SAML per tenant
- **Session Storage**: Django session with `current_tenant_id` and `current_tenant_slug`

### Authentication Flow Separation

```
┌─────────────────────────────────────────────────────────────────┐
│                    Django Application                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │  Django Account Users      │  │  Tenant Users            │  │
│  │  (Platform Admin)          │  │  (Tenant Members)        │  │
│  ├────────────────────────────┤  ├──────────────────────────┤  │
│  │ Model: User                │  │ Model: TenantUser        │  │
│  │ Login: /admin/             │  │ Login: /tenants/login/   │  │
│  │ Auth: Django auth          │  │ Auth: Django + SSO       │  │
│  │ SSO: No                    │  │ SSO: Yes (OIDC/SAML)     │  │
│  │ Roles: Staff/Superuser     │  │ Roles: Member/Admin/Own  │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### User Relationship

- A Django `User` record is created for both platform admins and tenant members
- Platform admins typically have `is_staff=True` or `is_superuser=True`
- Tenant members have a `TenantUser` record linking them to one or more tenants
- **A single User can be both**: A platform admin AND a member of multiple tenants
- Authentication context is determined by login URL and stored in session

### Session Context

When a user authenticates via tenant login:
```python
request.session['current_tenant_id'] = str(tenant.id)
request.session['current_tenant_slug'] = tenant.slug
```

This tenant context is used by decorators to enforce tenant-scoped access:
- `@tenant_member_required`: Verifies user is active member of tenant
- `@tenant_admin_required`: Verifies user has admin or owner role in tenant

## Project Structure

```
django-allauth-multitenant-sso/
├── src/
│   └── django_allauth_multitenant_sso/
│       ├── __init__.py                 # Package initialization
│       ├── apps.py                     # Django app configuration
│       ├── models.py                   # Data models (Tenant, TenantUser, SSOProvider, TenantInvitation)
│       ├── admin.py                    # Django admin configuration
│       ├── views.py                    # View handlers for SSO and tenant management
│       ├── urls.py                     # URL routing
│       ├── adapters.py                 # Custom django-allauth adapters
│       ├── providers.py                # OIDC and SAML provider clients
│       ├── forms.py                    # Django forms
│       ├── decorators.py               # Access control decorators
│       ├── migrations/                 # Database migrations
│       └── templates/                  # HTML templates
├── example/                            # Example Django project
│   ├── manage.py
│   └── demo/
│       ├── __init__.py
│       ├── settings.py                 # Configured for multi-tenant SSO
│       ├── urls.py
│       ├── wsgi.py
│       └── asgi.py
├── pyproject.toml                      # Package metadata and dependencies
├── README.md                           # Main documentation
├── LICENSE                             # MIT License
└── .gitignore

```

## Core Components

### 1. Models (models.py)

#### UUID7 for Primary Keys
All models use **UUID7** (time-ordered UUIDs) as primary keys instead of UUID4:
- **Better Database Performance**: UUID7s are time-ordered, providing better B-tree index performance
- **Sorted by Creation Time**: Natural sorting by creation time without additional timestamp field
- **Reduced Index Fragmentation**: Sequential-ish nature reduces database index fragmentation
- **Package**: Uses `uuid-utils` library for UUID7 generation

Benefits over UUID4:
- UUID4: Random UUIDs cause index fragmentation and poor sequential insert performance
- UUID7: Time-ordered with random suffix, combining benefits of sequential IDs and UUIDs

#### Tenant
- Represents an organization with its own SSO configuration
- Primary Key: UUID7 (time-ordered)
- Fields: name, slug, domain, sso_enabled, sso_enforced, signup_token
- Relations: Has many TenantUsers, SSOProviders, TenantInvitations

#### TenantUser
- Links users to tenants with role-based access
- Primary Key: UUID7 (time-ordered)
- Roles: member, admin, owner
- Stores external SSO identity ID
- Supports multi-tenant membership (one user, many tenants)

#### SSOProvider
- Stores SSO configuration per tenant
- Primary Key: UUID7 (time-ordered)
- Supports both OIDC and SAML protocols
- Includes testing metadata and status
- Only one active provider per tenant

#### TenantInvitation
- Manages user invitations to tenants
- Primary Key: UUID7 (time-ordered)
- Token: UUID7 string (for invitation URLs)
- Statuses: pending, accepted, expired, cancelled
- Token-based with expiration

### 2. Adapters (adapters.py)

#### MultiTenantAccountAdapter
- Extends django-allauth's DefaultAccountAdapter
- Enforces SSO when required by tenant
- Handles invitation-based signup
- Handles tenant-specific signup URLs
- Manages tenant-specific redirects

#### MultiTenantSocialAccountAdapter
- Extends django-allauth's DefaultSocialAccountAdapter
- Links SSO logins to tenant memberships
- Creates/updates TenantUser records on SSO login
- Stores external identity IDs

### 3. SSO Providers (providers.py)

#### OIDCProviderClient
- Handles OpenID Connect authentication flow
- Supports auto-discovery via issuer URL
- Methods:
  - `get_authorization_url()` - Start OIDC flow
  - `fetch_token()` - Exchange code for token
  - `get_userinfo()` - Retrieve user profile
  - `test_connection()` - Validate configuration

#### SAMLProviderClient
- Handles SAML 2.0 authentication flow
- Uses python3-saml library
- Methods:
  - `get_saml_settings()` - Generate SAML config
  - `test_connection()` - Validate configuration
- Generates SP metadata automatically

### 4. Views (views.py)

#### SSO Authentication Views
- `sso_login()` - Initiate SSO for tenant
- `oidc_callback()` - Handle OIDC redirect
- `saml_acs()` - SAML Assertion Consumer Service
- `saml_metadata()` - Generate SAML SP metadata

#### Tenant Management Views
- `tenant_dashboard()` - Admin dashboard
- `manage_sso_provider()` - Configure SSO
- `test_sso_provider()` - Test SSO config
- `toggle_sso()` - Enable/disable/enforce SSO
- `invite_user()` - Send invitations
- `tenant_signup()` - Handle tenant-specific signup URLs

#### Invitation Views
- `accept_invitation()` - Accept tenant invite

### 5. Access Control (decorators.py)

#### @tenant_member_required
- Verifies user is active member of tenant
- Stores tenant context in request

#### @tenant_admin_required
- Verifies user has admin or owner role
- Used for SSO configuration and user management

## Authentication Flow

### Platform Admin Authentication (Django Accounts)
1. User visits `/admin/` or `/accounts/login/`
2. Enters email and password
3. Django authenticates using `ModelBackend`
4. On success, user logged in with Django session
5. No tenant context is set
6. User can access Django admin interface if `is_staff=True`

### Tenant Member Authentication (Password)
1. User visits `/tenants/login/<tenant-slug>/`
2. System determines authentication method based on tenant SSO settings:
   - **SSO Enforced**: Automatically redirects to SSO provider
   - **SSO Optional**: Shows both SSO button and email/password form
   - **No SSO**: Shows only email/password form
3. User enters email and password (if password auth is allowed)
4. `MultiTenantAccountAdapter.pre_authenticate()` checks:
   - Does user have active `TenantUser` membership for this tenant?
   - If yes, proceed with authentication
   - If no, show error
5. On success, user logged in and tenant context set:
   ```python
   request.session['current_tenant_id'] = str(tenant.id)
   request.session['current_tenant_slug'] = tenant.slug
   ```

### SSO Authentication (OIDC)
1. User visits `/tenants/sso/login/<tenant-slug>/`
2. System validates tenant has SSO enabled
3. Redirects to OIDC provider authorization URL
4. User authenticates at IdP
5. IdP redirects to `/tenants/sso/oidc/callback/<tenant-slug>/`
6. System exchanges code for access token
7. Fetches user info from IdP
8. Creates/updates User and TenantUser records
9. Logs user in and sets tenant context

### SSO Authentication (SAML)
1. User visits `/tenants/sso/login/<tenant-slug>/`
2. System validates tenant has SSO enabled
3. Generates SAML AuthnRequest and redirects to IdP
4. User authenticates at IdP
5. IdP posts SAML Response to `/tenants/sso/saml/acs/<tenant-id>/`
6. System validates SAML assertion
7. Extracts user attributes
8. Creates/updates User and TenantUser records
9. Logs user in and sets tenant context

### Tenant-Specific Signup
1. User visits `/tenants/signup/<token>/`
2. System validates token and stores in session
3. User is redirected to signup page
4. After signup, `MultiTenantAccountAdapter.save_user()` creates TenantUser membership
5. User is logged in and redirected to tenant dashboard

## Multi-Tenant Isolation

This package provides **two layers of tenant data isolation** for defense-in-depth security:

### 1. Application-Level Isolation (Default - All Databases)

#### Session-Based Tenant Context
- Current tenant ID stored in session: `current_tenant_id`
- Current tenant slug stored in session: `current_tenant_slug`
- Set during login and SSO flows via `tenant_login()` view
- Used by decorators to enforce tenant-scoped operations

#### Role-Based Access Control
- Three roles: member, admin, owner
- Admins and owners can:
  - Configure SSO
  - Invite users
  - Manage tenant settings
  - View and manage tenant users
- Members have read-only access to tenant resources

#### QuerySet Filtering
- All tenant-specific queries filter by `tenant=current_tenant`
- Examples:
  ```python
  TenantUser.objects.filter(tenant=tenant)
  SSOProvider.objects.filter(tenant=tenant)
  TenantInvitation.objects.filter(tenant=tenant)
  ```
- Access control decorators verify tenant membership before allowing access

### 2. Database-Level Isolation with Row Level Security (PostgreSQL Only)

#### Overview
- **Optional** but **recommended for production**
- Requires PostgreSQL and `django-rls` package
- Provides database-level tenant isolation as a second layer of security
- Automatically filters all database queries at the PostgreSQL level
- Prevents data leaks even if application logic has bugs

#### How RLS Works
1. **Middleware Sets Tenant Context**:
   - `TenantRLSMiddleware` reads `current_tenant_id` from session
   - Calls `set_tenant(tenant_id)` to set PostgreSQL session variable
   - Database now knows which tenant's data to show

2. **PostgreSQL RLS Policies Enforce Isolation**:
   - Each tenant-specific model has RLS policies defined
   - Policies automatically filter all SELECT, INSERT, UPDATE, DELETE queries
   - Example: `WHERE tenant_id = current_setting('rls.tenant_id')::uuid`

3. **Models Configured for RLS**:
   - `TenantUser`: Inherits from `RLSModel`, filtered by `tenant_id`
   - `SSOProvider`: Inherits from `RLSModel`, filtered by `tenant_id`
   - `TenantInvitation`: Inherits from `RLSModel`, filtered by `tenant_id`
   - Database migration creates PostgreSQL RLS policies automatically

4. **Fallback Support**:
   - If `django-rls` is not installed, models inherit from `models.Model` instead
   - Application continues to work with application-level filtering only
   - Warning is issued when middleware is used without `django-rls`

#### Benefits of RLS
- **Defense in Depth**: Even if application logic fails, database prevents cross-tenant access
- **Compliance**: Meets strict security requirements for HIPAA, SOC 2, etc.
- **Transparent**: No changes to application queries needed
- **Performance**: PostgreSQL-level filtering is highly optimized
- **Audit Trail**: Database logs show tenant context for all queries

#### RLS Configuration
```python
# settings.py
INSTALLED_APPS = [
    ...
    'django_rls',  # Add django-rls
    ...
]

MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_allauth_multitenant_sso.middleware.TenantRLSMiddleware',  # Add RLS middleware
    ...
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # PostgreSQL required
        'NAME': 'your_database',
        ...
    }
}
```

#### Data Isolation Guarantee
- Each tenant has independent SSO configuration
- Users can belong to multiple tenants
- TenantUser model provides the many-to-many link
- No shared data between tenants
- With RLS: Database enforces isolation even if app code has bugs
- Without RLS: Application code enforces isolation through QuerySet filtering

## SSO Provider Configuration

### OIDC Setup
1. Tenant admin navigates to SSO settings
2. Selects OIDC protocol
3. Enters:
   - Provider name
   - Issuer URL (for auto-discovery) OR
   - Individual endpoints (authorize, token, userinfo)
   - Client ID and Secret
   - Scopes (default: openid email profile)
4. Tests connection
5. If successful, enables SSO

### SAML Setup
1. Tenant admin navigates to SSO settings
2. Selects SAML protocol
3. Downloads SP metadata from `/tenants/sso/saml/metadata/<tenant-id>/`
4. Configures IdP with SP metadata
5. Enters:
   - Provider name
   - Entity ID
   - SSO URL
   - X.509 Certificate
   - Attribute mapping (optional)
6. Tests connection
7. If successful, enables SSO

## Testing Strategy

### SSO Connection Testing
- `test_connection()` methods for both OIDC and SAML
- Validates:
  - OIDC: Issuer reachability, endpoint discovery
  - SAML: Entity ID, SSO URL, certificate format
- Results stored in `SSOProvider.test_results`
- Must pass before SSO can be enabled

### Admin Testing Flow
1. Configure SSO provider
2. Click "Test Configuration"
3. System performs connection test
4. Results displayed to admin
5. If successful, "Enable SSO" button appears
6. Admin can enable SSO for tenant

## Security Features

### Secrets Protection
- Client secrets and certificates stored in database
- Should be encrypted at rest in production
- Use Django's encryption or external secrets manager

### SAML Security
- Validates SAML signatures
- Checks assertion timestamps
- Verifies audience restrictions
- Configurable security settings

### OIDC Security
- Uses PKCE flow (can be added)
- Validates state parameter
- Verifies token signatures via JWKS
- Checks token expiration

### CSRF Protection
- Django CSRF middleware enabled
- SAML ACS endpoint uses `@csrf_exempt` (per SAML spec)
- State parameter provides CSRF protection for OIDC

## Extension Points

### Custom User Fields
- Override `_process_sso_user()` to map additional fields
- Customize attribute mapping in SAML configuration

### Custom Invitation Emails
- Implement email sending in `invite_user()` view
- Use Django's email system or third-party service

### Custom Templates
- Override templates in `templates/allauth_multitenant_sso/`
- Extend base templates for consistent styling

### Additional SSO Protocols
- Implement new provider client class
- Add to `get_provider_client()` factory function
- Add protocol choice to SSOProvider model

## Future Enhancements

### Planned Features
- [ ] Email notifications for invitations (implemented)
- [ ] Audit logging for SSO events
- [ ] Multi-factor authentication support
- [ ] Custom domain SSO discovery
- [ ] SCIM user provisioning
- [ ] OAuth2 client credentials flow
- [ ] API endpoints for programmatic access
- [ ] Webhook notifications
- [ ] Advanced RBAC with custom permissions
- [ ] SSO session management

### Performance Optimizations
- [ ] Cache SSO provider configurations
- [ ] Optimize database queries with select_related
- [ ] Add database indexes for common queries
- [ ] Implement Redis for session storage

## Security Features

### Field-Level Encryption

Sensitive SSO provider credentials are encrypted at rest using `django-fernet-fields`:

#### Encrypted Fields
- **`SSOProvider.oidc_client_secret`**: OIDC OAuth client secret (EncryptedCharField)
- **`SSOProvider.saml_x509_cert`**: SAML X.509 certificate (EncryptedTextField)

#### Encryption Implementation
- **Algorithm**: Fernet (symmetric encryption) - AES 128-bit in CBC mode with HMAC authentication
- **Library**: `django-fernet-fields` - transparent encryption/decryption
- **Key Storage**: Environment variable or Django settings (`FERNET_KEYS`)
- **Key Rotation**: Supports multiple keys for zero-downtime rotation

#### Security Benefits
1. **Database Dump Protection**: Encrypted data is useless without encryption keys
2. **Compliance**: Meets PCI-DSS, HIPAA, SOC 2 encryption at rest requirements
3. **Defense in Depth**: Additional layer beyond database permissions
4. **Transparent Usage**: Application code accesses fields normally

#### Configuration
```python
# settings.py
FERNET_KEYS = [
    'your-generated-encryption-key-here',
    'optional-old-key-for-rotation',
]
```

Generate keys:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**⚠️ Critical**: Losing encryption keys means losing access to encrypted data. Store keys securely in:
- Environment variables
- AWS Secrets Manager / Google Secret Manager
- HashiCorp Vault
- Kubernetes Secrets

## Dependencies

### Core Dependencies
- **Django** (>=4.2): Web framework
- **django-allauth** (>=0.57.0): Authentication framework
- **python3-saml** (>=1.15.0): SAML implementation
- **Authlib** (>=1.3.0): OIDC implementation
- **cryptography** (>=41.0.0): Cryptographic operations
- **django-fernet-fields** (>=0.6): Field-level encryption for sensitive data
- **uuid-utils** (>=0.9.0): UUID7 generation for time-ordered primary keys
- **django-rls** (>=1.0.0): Row Level Security for PostgreSQL (optional)

### Development Dependencies
- **pytest**: Testing framework
- **pytest-django**: Django testing utilities
- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking

## Contributing

See the [Contributing Guide](https://github.com/wshayes/django-allauth-multitenant-sso/blob/main/CONTRIBUTING.md) for contribution guidelines.
