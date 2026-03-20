"""
Management command to clean up expired invitations.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from damsso.models import TenantInvitation


class Command(BaseCommand):
    help = 'Mark expired invitations as expired and optionally delete old ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-expired',
            action='store_true',
            help='Delete expired invitations instead of just marking them',
        )
        parser.add_argument(
            '--delete-accepted',
            action='store_true',
            help='Delete accepted invitations older than specified days',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep accepted invitations (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )

    def handle(self, *args, **options):
        delete_expired = options.get('delete_expired')
        delete_accepted = options.get('delete_accepted')
        days = options.get('days')
        dry_run = options.get('dry_run')

        now = timezone.now()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made\n'))

        # Handle expired invitations
        expired_invitations = TenantInvitation.objects.filter(
            status='pending',
            expires_at__lt=now
        )

        expired_count = expired_invitations.count()

        if expired_count > 0:
            self.stdout.write(
                f'Found {expired_count} expired pending invitation(s)'
            )

            if not dry_run:
                if delete_expired:
                    expired_invitations.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Deleted {expired_count} expired invitation(s)')
                    )
                else:
                    expired_invitations.update(status='expired')
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Marked {expired_count} invitation(s) as expired')
                    )
            else:
                action = 'delete' if delete_expired else 'mark as expired'
                self.stdout.write(f'  Would {action} {expired_count} invitation(s)')
        else:
            self.stdout.write('No expired pending invitations found')

        # Handle old accepted invitations
        if delete_accepted:
            cutoff_date = now - timezone.timedelta(days=days)
            old_accepted = TenantInvitation.objects.filter(
                status='accepted',
                accepted_at__lt=cutoff_date
            )

            old_count = old_accepted.count()

            if old_count > 0:
                self.stdout.write(
                    f'\nFound {old_count} accepted invitation(s) older than {days} days'
                )

                if not dry_run:
                    old_accepted.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Deleted {old_count} old accepted invitation(s)')
                    )
                else:
                    self.stdout.write(f'  Would delete {old_count} invitation(s)')
            else:
                self.stdout.write(f'\nNo accepted invitations older than {days} days')

        if not dry_run:
            self.stdout.write('\n' + self.style.SUCCESS('Cleanup complete!'))
