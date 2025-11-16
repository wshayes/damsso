"""
Tests for email functionality in django-allauth-multitenant-sso.
"""
import pytest
from django.core import mail
from django.test import RequestFactory
from django_allauth_multitenant_sso.emails import (
    send_invitation_email,
    send_invitation_reminder_email,
    send_invitation_accepted_notification,
    send_bulk_invitations
)
from django_allauth_multitenant_sso.models import TenantInvitation


class TestSendInvitationEmail:
    """Tests for send_invitation_email function."""

    def test_sends_email_successfully(self, invitation):
        """Test invitation email is sent successfully."""
        result = send_invitation_email(invitation)

        assert result is True
        assert len(mail.outbox) == 1

        email = mail.outbox[0]
        assert invitation.email in email.to
        assert invitation.tenant.name in email.subject
        assert invitation.token in email.body

    def test_email_has_html_alternative(self, invitation):
        """Test invitation email includes HTML version."""
        send_invitation_email(invitation)

        email = mail.outbox[0]
        assert len(email.alternatives) > 0
        html_content = email.alternatives[0][0]
        assert 'text/html' in email.alternatives[0][1]
        assert invitation.token in html_content

    def test_email_contains_invitation_details(self, invitation):
        """Test email contains all necessary invitation details."""
        send_invitation_email(invitation)

        email = mail.outbox[0]
        body = email.body

        assert invitation.tenant.name in body
        assert invitation.get_role_display() in body
        assert invitation.token in body

    def test_email_with_request_context(self, invitation):
        """Test email generation with request context."""
        factory = RequestFactory()
        request = factory.get('/')

        result = send_invitation_email(invitation, request=request)
        assert result is True
        assert len(mail.outbox) == 1

    def test_handles_email_send_failure(self, invitation):
        """Test handles email backend failure gracefully."""
        with patch('django_allauth_multitenant_sso.emails.EmailMultiAlternatives.send') as mock_send:
            mock_send.side_effect = Exception('SMTP error')
            result = send_invitation_email(invitation)
            assert result is False


class TestSendInvitationReminderEmail:
    """Tests for send_invitation_reminder_email function."""

    def test_sends_reminder_for_pending_invitation(self, invitation):
        """Test reminder is sent for pending invitation."""
        result = send_invitation_reminder_email(invitation)

        assert result is True
        assert len(mail.outbox) == 1

    def test_does_not_send_for_expired_invitation(self, expired_invitation):
        """Test reminder is not sent for expired invitation."""
        result = send_invitation_reminder_email(expired_invitation)

        assert result is False
        assert len(mail.outbox) == 0

    def test_does_not_send_for_accepted_invitation(self, invitation):
        """Test reminder is not sent for accepted invitation."""
        invitation.status = 'accepted'
        invitation.save()

        result = send_invitation_reminder_email(invitation)

        assert result is False
        assert len(mail.outbox) == 0


class TestSendInvitationAcceptedNotification:
    """Tests for send_invitation_accepted_notification function."""

    def test_sends_notification_to_inviter(self, invitation):
        """Test notification is sent to inviter."""
        result = send_invitation_accepted_notification(invitation)

        assert result is True
        assert len(mail.outbox) == 1

        email = mail.outbox[0]
        assert invitation.invited_by.email in email.to
        assert invitation.email in email.subject
        assert invitation.tenant.name in email.subject

    def test_notification_contains_details(self, invitation):
        """Test notification contains acceptance details."""
        result = send_invitation_accepted_notification(invitation)

        email = mail.outbox[0]
        body = email.body

        assert invitation.email in body
        assert invitation.tenant.name in body
        assert invitation.get_role_display() in body

    def test_handles_notification_failure(self, invitation):
        """Test handles notification send failure."""
        with patch('django.core.mail.send_mail') as mock_send:
            mock_send.side_effect = Exception('SMTP error')
            result = send_invitation_accepted_notification(invitation)
            assert result is False


class TestSendBulkInvitations:
    """Tests for send_bulk_invitations function."""

    def test_sends_multiple_invitations(self, user, tenant):
        """Test sending multiple invitations."""
        invitations = [
            TenantInvitation.objects.create(
                tenant=tenant,
                email=f'user{i}@example.com',
                invited_by=user,
                role='member'
            )
            for i in range(3)
        ]

        stats = send_bulk_invitations(invitations)

        assert stats['total'] == 3
        assert stats['sent'] == 3
        assert stats['failed'] == 0
        assert len(mail.outbox) == 3

    def test_skips_non_pending_invitations(self, user, tenant):
        """Test skips invitations that are not pending."""
        invitations = []

        # Pending invitation (should be sent)
        invitations.append(TenantInvitation.objects.create(
            tenant=tenant,
            email='pending@example.com',
            invited_by=user,
            status='pending'
        ))

        # Accepted invitation (should be skipped)
        accepted = TenantInvitation.objects.create(
            tenant=tenant,
            email='accepted@example.com',
            invited_by=user,
            status='accepted'
        )
        invitations.append(accepted)

        stats = send_bulk_invitations(invitations)

        # Only one should be sent
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to[0] == 'pending@example.com'

    def test_handles_partial_failures(self, user, tenant):
        """Test handles some invitations failing."""
        invitations = [
            TenantInvitation.objects.create(
                tenant=tenant,
                email=f'user{i}@example.com',
                invited_by=user,
                role='member'
            )
            for i in range(3)
        ]

        with patch('django_allauth_multitenant_sso.emails.send_invitation_email') as mock_send:
            # First succeeds, second fails, third succeeds
            mock_send.side_effect = [True, False, True]

            stats = send_bulk_invitations(invitations)

            assert stats['total'] == 3
            assert stats['sent'] == 2
            assert stats['failed'] == 1
            assert len(stats['errors']) == 1

    def test_empty_list(self):
        """Test sending empty list of invitations."""
        stats = send_bulk_invitations([])

        assert stats['total'] == 0
        assert stats['sent'] == 0
        assert stats['failed'] == 0
        assert len(mail.outbox) == 0


# Import patch from unittest.mock
from unittest.mock import patch
