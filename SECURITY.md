# Security Policy

## Supported Versions

We actively support security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do NOT** create a public GitHub issue

Security vulnerabilities should be reported privately to prevent exploitation.

### 2. Email the maintainer

Send an email to: **william.s.hayes@gmail.com**

Include the following information:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)
- Your contact information

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution**: Depends on severity and complexity

### 4. Disclosure Policy

- We will acknowledge receipt of your report
- We will work with you to understand and resolve the issue
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We will coordinate public disclosure after a fix is available

## Security Best Practices

When using this package, please follow these security recommendations:

### 1. Keep Dependencies Updated

Regularly update all dependencies, including:
- Django
- django-allauth
- python3-saml
- authlib
- cryptography

### 2. Use HTTPS in Production

Always use HTTPS in production environments. Never transmit SSO credentials or tokens over unencrypted connections.

### 3. Protect Secrets

- Store client secrets and certificates securely
- Use environment variables or secret management systems
- Never commit secrets to version control
- Rotate credentials regularly

### 4. Validate SAML Signatures

Ensure SAML responses are properly validated:
- Verify X.509 certificates
- Validate SAML assertions
- Check signature algorithms

### 5. Implement Rate Limiting

Implement rate limiting on authentication endpoints to prevent brute force attacks.

### 6. Use Strong Session Management

- Use secure, HTTP-only cookies
- Implement proper session expiration
- Use CSRF protection (Django provides this by default)

### 7. Regular Security Audits

- Review SSO configurations regularly
- Audit user access and permissions
- Monitor for suspicious activity
- Keep security logs

### 8. Follow Django Security Guidelines

Follow Django's security best practices:
- Keep Django updated
- Use Django's security features
- Review Django security releases

## Known Security Considerations

### SSO Provider Configuration

- Always validate SSO provider certificates
- Use strong client secrets
- Implement proper redirect URI validation
- Monitor for unauthorized access attempts

### Multi-Tenant Isolation

- Ensure proper tenant isolation
- Validate tenant membership before granting access
- Use role-based access control appropriately

### User Invitations

- Use secure, time-limited invitation tokens
- Validate invitation tokens before acceptance
- Implement proper invitation expiration

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.0 → 0.1.1)
- Documented in CHANGELOG.md
- Tagged with security advisories on GitHub

## Additional Resources

- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [SAML Security Best Practices](https://kantarainitiative.github.io/SAMLprofiles/saml2int.html)

## Contact

For security concerns, email: **william.s.hayes@gmail.com**

Thank you for helping keep this project secure!

