"""
Management command to send or resend pending invitations.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_allauth_multitenant_sso.models import TenantInvitation
from django_allauth_multitenant_sso.emails import send_invitation_email, send_bulk_invitations


class Command(BaseCommand):
    help = 'Send or resend pending tenant invitations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-slug',
            type=str,
            help='Only send invitations for specific tenant',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Only send invitation to specific email',
        )
        parser.add_argument(
            '--token',
            type=str,
            help='Only send specific invitation by token',
        )
        parser.add_argument(
            '--resend',
            action='store_true',
            help='Resend all pending invitations (including previously sent)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        tenant_slug = options.get('tenant_slug')
        email = options.get('email')
        token = options.get('token')
        resend = options.get('resend')
        dry_run = options.get('dry_run')

        # Build queryset
        queryset = TenantInvitation.objects.filter(status='pending')

        # Apply filters
        if tenant_slug:
            queryset = queryset.filter(tenant__slug=tenant_slug)

        if email:
            queryset = queryset.filter(email=email)

        if token:
            queryset = queryset.filter(token=token)

        # Filter by validity
        queryset = queryset.filter(expires_at__gt=timezone.now())

        # Get invitations
        invitations = list(queryset.select_related('tenant', 'invited_by'))

        if not invitations:
            self.stdout.write(
                self.style.WARNING('No pending invitations found matching criteria')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {len(invitations)} pending invitation(s)')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No emails will be sent\n'))
            for invitation in invitations:
                self.stdout.write(
                    f'  Would send to: {invitation.email} '
                    f'(Tenant: {invitation.tenant.name}, '
                    f'Invited by: {invitation.invited_by.email})'
                )
            return

        # Confirm before sending
        if not resend:
            confirmation = input(f'\nSend {len(invitations)} invitation email(s)? [y/N]: ')
            if confirmation.lower() != 'y':
                self.stdout.write(self.style.WARNING('Cancelled'))
                return

        # Send invitations
        self.stdout.write('\nSending invitations...\n')

        sent = 0
        failed = 0

        for invitation in invitations:
            self.stdout.write(f'Sending to {invitation.email}...', ending=' ')

            try:
                if send_invitation_email(invitation):
                    self.stdout.write(self.style.SUCCESS('✓ Sent'))
                    sent += 1
                else:
                    self.stdout.write(self.style.ERROR('✗ Failed'))
                    failed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
                failed += 1

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Successfully sent: {sent}'))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f'Failed: {failed}'))
        self.stdout.write('='*50)
