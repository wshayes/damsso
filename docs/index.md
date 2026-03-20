# DAMSSO (Django Allauth Multitenant SSO)

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

## Quick Start

Get up and running in 5 minutes with our [Quick Start Guide](quickstart.md).

```bash
# Install the package
uv pip install damsso

# Or with pip
pip install damsso
```

## Documentation

### Getting Started

- **[Quick Start Guide](quickstart.md)** - Get up and running in 5 minutes
- **[Usage Guide](usage.md)** - How to use the package
- **[Configuration Guide](configuration.md)** - All configuration options
- **[Admin Guide](admin-guide.md)** - Understanding the Django admin interface

### Reference

- **[Models Reference](models.md)** - Data models and their fields
- **[API Reference](api-reference.md)** - Programmatic API
- **[Management Commands](management-commands.md)** - Command-line tools

### Advanced Topics

- **[Architecture](architecture.md)** - Technical architecture and design decisions
- **[Email Configuration](email-configuration.md)** - Email setup for various providers

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
uv pip install damsso
```

**Note:** While pip may work, this project is developed and tested with uv. For development, uv is required.

## Requirements

- Python 3.10+
- Django 4.2+
- django-allauth 0.57.0+
- python3-saml 1.15.0+
- authlib 1.3.0+
- cryptography 41.0.0+

## Example Project

See the `example/` directory in the repository for a complete working example.

## Support

- **GitHub Issues**: [Report an issue](https://github.com/wshayes/damsso/issues)
- **Documentation**: This site
- **Repository**: [View on GitHub](https://github.com/wshayes/damsso)

## License

MIT License - see [LICENSE](https://github.com/wshayes/damsso/blob/main/LICENSE) file for details

## Additional Resources

- [Contributing Guide](https://github.com/wshayes/damsso/blob/main/CONTRIBUTING.md) - How to contribute to the project
- [Security Policy](https://github.com/wshayes/damsso/blob/main/SECURITY.md) - Security reporting and best practices
- [Changelog](https://github.com/wshayes/damsso/blob/main/CHANGELOG.md) - Version history and changes
