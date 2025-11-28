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
- django-fernet-fields
- uuid-utils
- django-rls (if using PostgreSQL RLS)

### 2. Use HTTPS in Production

Always use HTTPS in production environments. Never transmit SSO credentials or tokens over unencrypted connections.

### 3. Protect Secrets and Encryption Keys

#### Field-Level Encryption

This package automatically encrypts sensitive SSO provider credentials at rest using **Fernet symmetric encryption** (AES 128-bit CBC + HMAC):
- **OIDC Client Secrets**: `SSOProvider.oidc_client_secret` (encrypted)
- **SAML X.509 Certificates**: `SSOProvider.saml_x509_cert` (encrypted)

**Implementation**: Custom encrypted fields based on Django's BinaryField with transparent encryption/decryption using the `cryptography` library.

#### Encryption Key Management

**CRITICAL**: Properly manage your `FERNET_KEYS` encryption keys:

1. **Generate Strong Keys**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Store Keys Securely**
   - ✅ Environment variables: `export FERNET_KEYS='["your-key-here"]'`
   - ✅ AWS Secrets Manager / Google Secret Manager
   - ✅ HashiCorp Vault
   - ✅ Kubernetes Secrets
   - ❌ NEVER commit to version control
   - ❌ NEVER hardcode in settings.py for production

3. **Key Rotation Best Practices**
   - Keep old keys during rotation period:
     ```python
     FERNET_KEYS = [
         'new-key',  # Used for new encryptions
         'old-key',  # Can still decrypt existing data
     ]
     ```
   - After rotation, re-encrypt old data:
     ```bash
     python manage.py rotate_fernet_keys
     ```
   - Remove old keys only after all data is re-encrypted

4. **Backup Strategies**
   - Store encryption keys SEPARATELY from database backups
   - Encrypted database backup + lost keys = permanent data loss
   - Use separate key backup location (different cloud region/provider)
   - Document key recovery procedures

5. **Disaster Recovery**
   - Test key restoration procedures regularly
   - Ensure team has access to key backups
   - Document emergency key rotation process

#### Other Secrets Management

- Store OAuth client secrets and certificates securely
- Use environment variables or secret management systems
- Never commit secrets to version control
- Rotate credentials regularly
- Audit secret access logs

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

### Field Encryption

- **Encryption Keys**: Loss of `FERNET_KEYS` results in permanent data loss
- **Key Rotation**: Plan key rotation before keys are compromised
- **Key Storage**: Use dedicated secrets management (Vault, Secrets Manager)
- **Backup Separation**: Store keys separately from encrypted database backups
- **Algorithm**: Uses Fernet (AES-128 CBC + HMAC) for authenticated encryption

### SSO Provider Configuration

- Always validate SSO provider certificates
- Use strong client secrets (encrypted automatically)
- Implement proper redirect URI validation
- Monitor for unauthorized access attempts
- Certificates are encrypted at rest in database

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

