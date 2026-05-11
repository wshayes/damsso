# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-05-11

### Added
- Per-membership `auth_method` escape hatch on `TenantUser` and `TenantInvitation`
  (`'sso'` or `'local'`). Overrides tenant-wide SSO enforcement for specific
  users (contractors, break-glass accounts, users on non-federated domains).
- `SSORoutingAccountAdapterMixin` and `SSORoutingSocialAccountAdapterMixin` —
  composable mixins so host apps can add damsso's SSO routing to their own
  `DefaultAccountAdapter` subclasses instead of inheriting the full adapter.
- Host-app integration settings:
  - `DAMSSO_EXTRA_MIGRATION_DEPENDENCIES` — inject extra dependencies into
    specific damsso migrations.
  - `DAMSSO_ENABLE_RLS` — make the bundled RLS migration a no-op when the
    host project manages RLS itself.
  - `DAMSSO_RLS_BYPASS_PREDICATE` — override the admin-bypass SQL fragment
    used in damsso's RLS policies.
  - `DAMSSO_USE_BUILTIN_INVITATIONS` — hide damsso's `TenantInvitation`
    admin when the host ships its own invitation flow.
- `docs/host-app-integration.md` — end-to-end guide for dropping damsso
  into an existing Django project (swap-mode setup).

### Changed
- Migrations 0001, 0002, 0004, 0006, 0009 are now swap-aware: Tenant
  CreateModel/AlterField/AddField operations only run in standalone mode
  (`DAMSSO_TENANT_MODEL == 'damsso.Tenant'`).
- The hardcoded `('tenants', '0002_subdomain_slug')` dependency in
  migrations 0001 and 0003 is removed in favor of the new
  `DAMSSO_EXTRA_MIGRATION_DEPENDENCIES` setting.
- `tenant_login` view: replaced the unconditional SSO redirect when
  `tenant.sso_enforced` with a per-membership check. Tenants without any
  local-auth members still auto-redirect; tenants with at least one local
  member render the full login form.
- Admin registration is consolidated into `register_damsso_admin()` and
  honors `DAMSSO_USE_BUILTIN_INVITATIONS`. `register_damsso_tenant_admin`
  is kept as a back-compat alias.
- `MultiTenantAccountAdapter` / `MultiTenantSocialAccountAdapter` are now
  thin combinations of the new mixins with allauth's defaults.
- Session keys: `sso_tenant_pk` is the canonical key; the legacy
  `sso_tenant_id` is still written and read for backwards compatibility.

### Fixed
- SSO callback (`_process_sso_user`) refuses to log in users whose existing
  membership is marked `auth_method='local'` (symmetric to the password-side
  block).

## [0.1.0] - 2024-12-XX

### Added
- Multi-tenant support with separate SSO configurations per tenant
- OIDC provider integration with issuer discovery and manual endpoint configuration
- SAML provider integration with X.509 certificate support
- SSO testing functionality for tenant admins
- User invitation system with email notifications
- Customizable HTML and plain text email templates
- Invitation acceptance notifications to inviters
- Management commands for invitation management:
  - `send_pending_invitations` - Send or resend invitation emails
  - `cleanup_invitations` - Clean up expired or old invitations
  - `list_invitations` - View all invitations with filtering options
- Django admin integration for tenant and SSO provider management
- Role-based access control (member, admin, owner) per tenant
- SSO enforcement option (disable password authentication)
- Decorators for tenant access control:
  - `@tenant_member_required` - Ensures user is a member of the tenant
  - `@tenant_admin_required` - Ensures user is admin/owner of tenant
- Example project demonstrating usage
- Comprehensive test suite with 103 tests covering core functionality
- Documentation including:
  - README with installation and usage guide
  - Architecture documentation
  - Email configuration guide
  - Quick start guide
  - Test coverage report

[0.1.0]: https://github.com/wshayes/damsso/releases/tag/v0.1.0

