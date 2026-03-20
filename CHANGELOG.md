# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

