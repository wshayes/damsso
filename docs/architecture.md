# Django Allauth Multi-Tenant SSO - Architecture

## Overview

This package extends django-allauth to provide dynamic, per-tenant SSO configuration using OIDC and SAML protocols. Each tenant can have its own SSO provider, and users can belong to multiple tenants.

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

#### Tenant
- Represents an organization with its own SSO configuration
- Fields: name, slug, domain, sso_enabled, sso_enforced, signup_token
- Relations: Has many TenantUsers, SSOProviders, TenantInvitations

#### TenantUser
- Links users to tenants with role-based access
- Roles: member, admin, owner
- Stores external SSO identity ID
- Supports multi-tenant membership (one user, many tenants)

#### SSOProvider
- Stores SSO configuration per tenant
- Supports both OIDC and SAML protocols
- Includes testing metadata and status
- Only one active provider per tenant

#### TenantInvitation
- Manages user invitations to tenants
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

### Password Authentication
1. User visits `/accounts/login/`
2. Enters email and password
3. `MultiTenantAccountAdapter.pre_authenticate()` checks:
   - Does user belong to tenant with enforced SSO?
   - If yes, redirect to SSO login
   - If no, proceed with password auth
4. On success, user logged in and tenant context set

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

### Session-Based Tenant Context
- Current tenant ID stored in session: `current_tenant_id`
- Set during login and SSO flows
- Used for tenant-scoped operations

### Role-Based Access Control
- Three roles: member, admin, owner
- Admins and owners can:
  - Configure SSO
  - Invite users
  - Manage tenant settings
- Members have read-only access

### Data Isolation
- Each tenant has independent SSO configuration
- Users can belong to multiple tenants
- TenantUser model provides the link
- No shared data between tenants

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

## Dependencies

### Core Dependencies
- **Django** (>=4.2): Web framework
- **django-allauth** (>=0.57.0): Authentication framework
- **python3-saml** (>=1.15.0): SAML implementation
- **Authlib** (>=1.3.0): OIDC implementation
- **cryptography** (>=41.0.0): Cryptographic operations

### Development Dependencies
- **pytest**: Testing framework
- **pytest-django**: Django testing utilities
- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking

## Contributing

See the [Contributing Guide](https://github.com/wshayes/django-allauth-multitenant-sso/blob/main/CONTRIBUTING.md) for contribution guidelines.
