# Email Configuration Guide

This guide explains how to configure email notifications for tenant invitations.

## Overview

The package sends email notifications for:
1. **Invitation emails** - Sent to users when they're invited to a tenant
2. **Acceptance notifications** - Sent to inviters when users accept invitations

## Development Setup

For development, use the console email backend to print emails to the terminal:

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@example.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@example.com'
```

Emails will be printed to your terminal when invitations are sent.

## Production Setup

### Using Gmail (SMTP)

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password, not regular password
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
MULTITENANT_INVITATION_REPLY_TO_INVITER = True
```

**Note:** For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use the App Password instead of your regular password

### Using SendGrid

```python
# Install: pip install sendgrid
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = 'your-sendgrid-api-key'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
```

### Using Amazon SES

```python
# Install: pip install django-ses
EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_SES_REGION_NAME = 'us-east-1'
AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
```

### Using Mailgun

```python
# Install: pip install django-anymail
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
ANYMAIL = {
    'MAILGUN_API_KEY': 'your-mailgun-api-key',
    'MAILGUN_SENDER_DOMAIN': 'mg.yourdomain.com',
}
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
```

### Using Postmark

```python
# Install: pip install django-anymail
EMAIL_BACKEND = 'anymail.backends.postmark.EmailBackend'
ANYMAIL = {
    'POSTMARK_SERVER_TOKEN': 'your-postmark-server-token',
}
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
```

## Configuration Options

### Required Settings

```python
# The email backend to use
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Default "from" address for all emails
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

### Optional Settings

```python
# Site name (used in email templates)
SITE_NAME = 'Your Platform Name'

# Site domain (used for building absolute URLs in emails)
SITE_DOMAIN = 'yourdomain.com'

# Specific "from" address for invitation emails
MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'

# Set reply-to as the inviter's email (allows direct replies)
MULTITENANT_INVITATION_REPLY_TO_INVITER = True

# Server email (for error notifications)
SERVER_EMAIL = 'server@yourdomain.com'
```

## Customizing Email Templates

### Template Files

The package includes three email templates:

1. **Subject** - `allauth_multitenant_sso/email/invitation_subject.txt`
2. **Plain Text Body** - `allauth_multitenant_sso/email/invitation_message.txt`
3. **HTML Body** - `allauth_multitenant_sso/email/invitation_message.html`

### Overriding Templates

Create your own templates in your project's `templates/` directory:

```
your_project/
└── templates/
    └── allauth_multitenant_sso/
        └── email/
            ├── invitation_subject.txt
            ├── invitation_message.txt
            └── invitation_message.html
```

### Template Context

Available variables in templates:

- `invitation` - The TenantInvitation object
- `tenant_name` - Name of the tenant
- `role` - Display name of the role (e.g., "Member")
- `invited_by_name` - Name of the person who sent the invitation
- `invited_by_email` - Email of the inviter
- `invitation_url` - Full URL to accept the invitation
- `expires_at` - Formatted expiration date
- `site_name` - Your site's name
- `domain` - Your site's domain

### Example Custom Template

**invitation_subject.txt:**
```
Welcome to {{ tenant_name }}!
```

**invitation_message.txt:**
```
Hi there!

{{ invited_by_name }} has invited you to join {{ tenant_name }}.

Click here to accept: {{ invitation_url }}

This invitation expires on {{ expires_at }}.

Best regards,
{{ site_name }}
```

## Testing Email Configuration

### Test from Django Shell

```python
from django.core.mail import send_mail

send_mail(
    'Test Subject',
    'Test message',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

### Test Invitation Email

```python
from django_allauth_multitenant_sso.models import TenantInvitation
from django_allauth_multitenant_sso.emails import send_invitation_email

# Get a pending invitation
invitation = TenantInvitation.objects.filter(status='pending').first()

# Send test email
if invitation:
    send_invitation_email(invitation)
```

### Using Management Command

```bash
# Send all pending invitations (with confirmation prompt)
python manage.py send_pending_invitations

# Dry run - see what would be sent
python manage.py send_pending_invitations --dry-run
```

## Troubleshooting

### Emails Not Sending

1. **Check email backend configuration**
   ```python
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.EMAIL_BACKEND)
   ```

2. **Test basic email sending**
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Body', 'from@example.com', ['to@example.com'])
   ```

3. **Check for errors in logs**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Gmail-Specific Issues

- **"Username and Password not accepted"**
  - Enable 2FA on your Google account
  - Create an App Password
  - Use the App Password instead of your regular password

- **"Less secure app access"**
  - Google has disabled this. Use App Passwords instead.

### SendGrid Issues

- **"Invalid API Key"**
  - Verify your API key is correct
  - Check that the API key has "Mail Send" permissions

- **Domain not verified**
  - Verify your sender domain in SendGrid dashboard
  - Use a verified domain in `DEFAULT_FROM_EMAIL`

### Production Checklist

- [ ] Configure production email backend
- [ ] Use environment variables for sensitive settings
- [ ] Verify sender domain (SPF, DKIM, DMARC)
- [ ] Test email sending in production environment
- [ ] Set up email monitoring/logging
- [ ] Configure bounce handling
- [ ] Set up unsubscribe mechanism (if needed)
- [ ] Test email deliverability (spam filters)
- [ ] Configure rate limiting if needed
- [ ] Set up email templates with your branding

## Environment Variables

Store email credentials securely using environment variables:

```python
# settings.py
import os

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
```

**`.env` file:**
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

**Using python-decouple:**
```bash
pip install python-decouple
```

```python
from decouple import config

EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

## Advanced Configuration

### Custom Email Class

For advanced customization, create a custom email function:

```python
# yourapp/emails.py
from django_allauth_multitenant_sso.emails import send_invitation_email as base_send

def send_invitation_email(invitation, request=None):
    # Add custom logic here
    # Log to analytics, etc.

    return base_send(invitation, request)
```

### Asynchronous Email Sending

For better performance, send emails asynchronously using Celery:

```python
# tasks.py
from celery import shared_task
from django_allauth_multitenant_sso.emails import send_invitation_email

@shared_task
def send_invitation_email_async(invitation_id):
    from django_allauth_multitenant_sso.models import TenantInvitation
    invitation = TenantInvitation.objects.get(id=invitation_id)
    return send_invitation_email(invitation)
```

```python
# In your view or adapter
send_invitation_email_async.delay(invitation.id)
```

## Support

For email-related issues:
1. Check the [troubleshooting section](#troubleshooting)
2. Review Django's email documentation
3. Check your email provider's documentation
4. Open an issue on GitHub with email backend details (without sensitive info)
