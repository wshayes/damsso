"""
Email utilities for multi-tenant SSO.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.utils import timezone
from .models import TenantInvitation
import logging


logger = logging.getLogger(__name__)


def send_invitation_email(invitation: TenantInvitation, request=None):
    """
    Send invitation email to a user.

    Args:
        invitation: TenantInvitation instance
        request: Optional Django request object for building absolute URLs

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get site information
        if request:
            site = get_current_site(request)
            site_name = site.name
            domain = site.domain
            protocol = 'https' if request.is_secure() else 'http'
        else:
            site_name = getattr(settings, 'SITE_NAME', 'Our Platform')
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
            protocol = 'https' if not settings.DEBUG else 'http'

        # Build invitation URL
        from django.urls import reverse
        invitation_path = reverse(
            'allauth_multitenant_sso:accept_invitation',
            kwargs={'token': invitation.token}
        )
        invitation_url = f"{protocol}://{domain}{invitation_path}"

        # Prepare context for email templates
        context = {
            'invitation': invitation,
            'tenant_name': invitation.tenant.name,
            'role': invitation.get_role_display(),
            'invited_by_name': invitation.invited_by.get_full_name() or invitation.invited_by.email,
            'invited_by_email': invitation.invited_by.email,
            'invitation_url': invitation_url,
            'expires_at': invitation.expires_at.strftime('%B %d, %Y at %I:%M %p %Z'),
            'site_name': site_name,
            'domain': domain,
        }

        # Render email subject (remove newlines)
        subject = render_to_string(
            'allauth_multitenant_sso/email/invitation_subject.txt',
            context
        ).strip()

        # Render plain text message
        text_message = render_to_string(
            'allauth_multitenant_sso/email/invitation_message.txt',
            context
        )

        # Render HTML message
        html_message = render_to_string(
            'allauth_multitenant_sso/email/invitation_message.html',
            context
        )

        # Get from email
        from_email = getattr(
            settings,
            'MULTITENANT_INVITATION_FROM_EMAIL',
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        )

        # Create email with both plain text and HTML versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=from_email,
            to=[invitation.email],
            reply_to=[invitation.invited_by.email] if getattr(
                settings,
                'MULTITENANT_INVITATION_REPLY_TO_INVITER',
                False
            ) else None
        )
        email.attach_alternative(html_message, "text/html")

        # Send email
        email.send(fail_silently=False)

        logger.info(
            f"Invitation email sent to {invitation.email} for tenant {invitation.tenant.name}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send invitation email to {invitation.email}: {str(e)}",
            exc_info=True
        )
        return False


def send_invitation_reminder_email(invitation: TenantInvitation, request=None):
    """
    Send a reminder email for a pending invitation.

    Args:
        invitation: TenantInvitation instance
        request: Optional Django request object

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if invitation.status != 'pending' or not invitation.is_valid():
        logger.warning(
            f"Attempted to send reminder for invalid invitation {invitation.id}"
        )
        return False

    # For now, we'll reuse the same template
    # You could create a separate reminder template if desired
    return send_invitation_email(invitation, request)


def send_invitation_accepted_notification(invitation: TenantInvitation, request=None):
    """
    Send notification to the inviter when an invitation is accepted.

    Args:
        invitation: TenantInvitation instance
        request: Optional Django request object

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get site information
        if request:
            site = get_current_site(request)
            site_name = site.name
            domain = site.domain
        else:
            site_name = getattr(settings, 'SITE_NAME', 'Our Platform')
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')

        # Prepare context
        context = {
            'invitation': invitation,
            'tenant_name': invitation.tenant.name,
            'accepted_user_email': invitation.email,
            'role': invitation.get_role_display(),
            'site_name': site_name,
            'tenant_slug': invitation.tenant.slug,
        }

        # Simple subject and message (you can create templates for these too)
        subject = f"{invitation.email} accepted your invitation to {invitation.tenant.name}"

        message = f"""Hi {invitation.invited_by.get_full_name() or invitation.invited_by.email},

Good news! {invitation.email} has accepted your invitation to join {invitation.tenant.name}.

They are now a {invitation.get_role_display()} in your organization.

Thanks,
The {site_name} Team
"""

        from_email = getattr(
            settings,
            'MULTITENANT_INVITATION_FROM_EMAIL',
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        )

        # Send email
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[invitation.invited_by.email],
            fail_silently=False
        )

        logger.info(
            f"Acceptance notification sent to {invitation.invited_by.email} "
            f"for {invitation.email} joining {invitation.tenant.name}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to send acceptance notification to {invitation.invited_by.email}: {str(e)}",
            exc_info=True
        )
        return False


def send_bulk_invitations(invitations, request=None):
    """
    Send multiple invitation emails in bulk.

    Args:
        invitations: QuerySet or list of TenantInvitation instances
        request: Optional Django request object

    Returns:
        dict: Statistics about sent emails
    """
    stats = {
        'total': len(invitations),
        'sent': 0,
        'failed': 0,
        'errors': []
    }

    for invitation in invitations:
        if invitation.status != 'pending':
            continue

        try:
            if send_invitation_email(invitation, request):
                stats['sent'] += 1
            else:
                stats['failed'] += 1
                stats['errors'].append(
                    f"Failed to send invitation to {invitation.email}"
                )
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append(
                f"Error sending to {invitation.email}: {str(e)}"
            )

    logger.info(
        f"Bulk invitation send complete: {stats['sent']} sent, "
        f"{stats['failed']} failed out of {stats['total']} total"
    )

    return stats
