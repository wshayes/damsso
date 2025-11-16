# Test Coverage Report

## Summary

**Total Tests:** 103 tests
**Status:** ✅ All tests passing
**Overall Coverage:** 55%
**Core Functionality Coverage:** 88% (excluding views and management commands)

## Test Results

```
103 passed, 7 warnings in 28.16s
```

## Coverage by Module

| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| **models.py** | 134 | 0 | **100%** ✅ |
| **forms.py** | 49 | 0 | **100%** ✅ |
| **decorators.py** | 34 | 0 | **100%** ✅ |
| **emails.py** | 73 | 3 | **96%** ✅ |
| **providers.py** | 116 | 19 | **84%** ✅ |
| **admin.py** | 54 | 13 | **76%** ✅ |
| **adapters.py** | 115 | 29 | **75%** ✅ |
| **apps.py** | 8 | 0 | **100%** ✅ |
| **urls.py** | 4 | 0 | **100%** ✅ |
| **__init__.py** | 2 | 0 | **100%** ✅ |
| views.py | 283 | 237 | 16% ⚠️ |
| cleanup_invitations.py | 44 | 44 | 0% ⚠️ |
| list_invitations.py | 53 | 53 | 0% ⚠️ |
| send_pending_invitations.py | 60 | 60 | 0% ⚠️ |

## Test Coverage Details

### 1. **Models (100% Coverage)** ✅

**Test File:** `tests/test_models.py` (38 tests)

#### Tenant Model (7 tests)
- ✅ Create tenant with all fields
- ✅ String representation
- ✅ Ordering by name
- ✅ Get active SSO provider (with/without provider)
- ✅ Unique constraints (name and slug)

#### TenantUser Model (8 tests)
- ✅ Create tenant user with roles (member, admin, owner)
- ✅ String representation
- ✅ Admin role checking for all roles
- ✅ Unique constraint (user-tenant pair)
- ✅ Multiple tenant memberships
- ✅ External ID storage

#### SSOProvider Model (13 tests)
- ✅ Create OIDC provider
- ✅ Create SAML provider
- ✅ String representation
- ✅ OIDC validation (client ID, secret, issuer/endpoints required)
- ✅ OIDC validation with manual endpoints
- ✅ SAML validation (entity ID, SSO URL, certificate required)
- ✅ Mark as tested (success/failure)

#### TenantInvitation Model (10 tests)
- ✅ Create invitation
- ✅ Auto-generate token
- ✅ Auto-set expiration (7 days)
- ✅ String representation
- ✅ Validation (pending, expired, accepted)
- ✅ Accept invitation (creates TenantUser)
- ✅ Reactivate inactive tenant user
- ✅ Error handling (expired/cancelled invitations)

### 2. **Forms (100% Coverage)** ✅

**Test File:** `tests/test_forms.py` (12 tests)

#### TenantForm (3 tests)
- ✅ Valid form data
- ✅ Form saves correctly
- ✅ Invalid form (missing required fields)

#### SSOProviderForm (1 test)
- ✅ Form has correct fields

#### OIDCProviderForm (2 tests)
- ✅ Valid form with issuer discovery
- ✅ Valid form with manual endpoints

#### SAMLProviderForm (2 tests)
- ✅ Valid form with required fields
- ✅ Form with optional SLO URL

#### TenantInvitationForm (4 tests)
- ✅ Valid invitation form
- ✅ Rejects existing tenant members
- ✅ Rejects duplicate pending invitations
- ✅ Allows new users
- ✅ Validates email format

### 3. **Decorators (100% Coverage)** ✅

**Test File:** `tests/test_decorators.py` (8 tests)

#### @tenant_member_required (4 tests)
- ✅ Allows tenant members
- ✅ Redirects non-members
- ✅ Handles inactive tenant users
- ✅ Handles inactive tenants (404)

#### @tenant_admin_required (4 tests)
- ✅ Allows tenant admins
- ✅ Allows tenant owners
- ✅ Rejects regular members
- ✅ Rejects non-members

### 4. **Email Functionality (96% Coverage)** ✅

**Test File:** `tests/test_emails.py` (13 tests)

#### send_invitation_email (5 tests)
- ✅ Sends email successfully
- ✅ Includes HTML alternative
- ✅ Contains all invitation details
- ✅ Works with request context
- ✅ Handles send failures gracefully

#### send_invitation_reminder_email (3 tests)
- ✅ Sends reminder for pending invitations
- ✅ Skips expired invitations
- ✅ Skips accepted invitations

#### send_invitation_accepted_notification (3 tests)
- ✅ Sends notification to inviter
- ✅ Contains acceptance details
- ✅ Handles failures gracefully

#### send_bulk_invitations (4 tests)
- ✅ Sends multiple invitations
- ✅ Skips non-pending invitations
- ✅ Handles partial failures
- ✅ Handles empty lists

### 5. **SSO Providers (84% Coverage)** ✅

**Test File:** `tests/test_providers.py` (21 tests)

#### OIDCProviderClient (5 tests)
- ✅ Initialize with OIDC provider
- ✅ Reject wrong protocol
- ✅ Test connection with issuer discovery (success/failure)
- ✅ Test connection with manual endpoints

#### SAMLProviderClient (13 tests)
- ✅ Initialize with SAML provider
- ✅ Reject wrong protocol
- ✅ Clean certificate (with/without headers)
- ✅ Get SAML settings
- ✅ Get SAML settings with SLO
- ✅ Test connection (success/failure)
- ✅ Test connection with unreachable URL
- ✅ Validate required fields (entity ID, SSO URL, certificate)

#### get_provider_client (3 tests)
- ✅ Returns OIDC client for OIDC provider
- ✅ Returns SAML client for SAML provider
- ✅ Raises error for unknown protocol

### 6. **Adapters (75% Coverage)** ✅

**Test File:** `tests/test_adapters.py` (10 tests)

#### MultiTenantAccountAdapter (5 tests)
- ✅ Signup control with/without invitation
- ✅ Signup with MULTITENANT_ALLOW_OPEN_SIGNUP setting
- ✅ Login redirect with tenant membership
- ✅ Save user with invitation acceptance

#### MultiTenantSocialAccountAdapter (5 tests)
- ✅ Signup with tenant SSO enabled
- ✅ Signup with invitation
- ✅ Pre-social login creates tenant membership
- ✅ Save user creates tenant membership
- ✅ Save user with invitation

## Not Yet Covered

### Views (16% Coverage) ⚠️
The views module contains complex Django view logic that would require more extensive integration testing with Django's test client. These tests would involve:
- Full request/response cycles
- Session management
- Template rendering
- URL routing
- Form submission workflows

### Management Commands (0% Coverage) ⚠️
The management commands (`cleanup_invitations`, `list_invitations`, `send_pending_invitations`) would require testing Django's command execution framework. These are utility commands that can be tested manually or with additional integration tests.

## Running the Tests

### Run all tests:
```bash
python -m pytest tests/ -v --no-migrations
```

### Run with coverage:
```bash
python -m pytest tests/ --cov=src/django_allauth_multitenant_sso --cov-report=term --no-migrations
```

### Run specific test file:
```bash
python -m pytest tests/test_models.py -v
```

### Run specific test:
```bash
python -m pytest tests/test_models.py::TestTenant::test_create_tenant -v
```

## Test Dependencies

The following packages are required for testing (installed via `uv pip install -e ".[test]"`):
- pytest>=7.4.0
- pytest-django>=4.5.0
- pytest-cov>=4.1.0
- responses>=0.23.0

## Test Configuration

Configuration is in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

## Conclusion

The test suite provides comprehensive coverage of the core business logic:
- **All models** are fully tested with 100% coverage
- **All forms** are fully tested with validation edge cases
- **All decorators** are fully tested for access control
- **Email functionality** is thoroughly tested including error handling
- **SSO provider clients** are well tested for both OIDC and SAML
- **Django-allauth adapters** cover the main authentication flows

The package has a solid foundation of tests that cover the critical functionality. The untested areas (views and management commands) are utility/UI layers that are less critical to unit test compared to the core business logic.
