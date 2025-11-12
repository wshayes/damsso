"""
Management command to list tenant invitations.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_allauth_multitenant_sso.models import TenantInvitation

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


class Command(BaseCommand):
    help = 'List tenant invitations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-slug',
            type=str,
            help='Filter by tenant slug',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'accepted', 'expired', 'cancelled'],
            help='Filter by status',
        )
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Show only expired pending invitations',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'simple', 'json'],
            default='table',
            help='Output format',
        )

    def handle(self, *args, **options):
        tenant_slug = options.get('tenant_slug')
        status = options.get('status')
        show_expired = options.get('expired')
        output_format = options.get('format')

        # Build queryset
        queryset = TenantInvitation.objects.all().select_related(
            'tenant', 'invited_by'
        ).order_by('-created_at')

        # Apply filters
        if tenant_slug:
            queryset = queryset.filter(tenant__slug=tenant_slug)

        if status:
            queryset = queryset.filter(status=status)

        if show_expired:
            queryset = queryset.filter(
                status='pending',
                expires_at__lt=timezone.now()
            )

        invitations = list(queryset)

        if not invitations:
            self.stdout.write(
                self.style.WARNING('No invitations found matching criteria')
            )
            return

        # Prepare data
        if output_format == 'json':
            import json
            data = []
            for inv in invitations:
                data.append({
                    'token': inv.token,
                    'email': inv.email,
                    'tenant': inv.tenant.slug,
                    'tenant_name': inv.tenant.name,
                    'role': inv.role,
                    'status': inv.status,
                    'invited_by': inv.invited_by.email,
                    'created_at': inv.created_at.isoformat(),
                    'expires_at': inv.expires_at.isoformat(),
                    'is_valid': inv.is_valid(),
                })
            self.stdout.write(json.dumps(data, indent=2))

        else:
            # Table format
            headers = [
                'Email',
                'Tenant',
                'Role',
                'Status',
                'Invited By',
                'Created',
                'Expires',
                'Valid'
            ]

            rows = []
            for inv in invitations:
                rows.append([
                    inv.email,
                    inv.tenant.name[:20],
                    inv.get_role_display(),
                    inv.status,
                    inv.invited_by.email[:20],
                    inv.created_at.strftime('%Y-%m-%d'),
                    inv.expires_at.strftime('%Y-%m-%d'),
                    '✓' if inv.is_valid() else '✗'
                ])

            if HAS_TABULATE:
                if output_format == 'table':
                    self.stdout.write(
                        '\n' + tabulate(rows, headers=headers, tablefmt='grid')
                    )
                else:
                    self.stdout.write(
                        '\n' + tabulate(rows, headers=headers, tablefmt='simple')
                    )
            else:
                # Fallback to simple format if tabulate not available
                self.stdout.write('\n' + ' | '.join(headers))
                self.stdout.write('\n' + '-' * 100)
                for row in rows:
                    self.stdout.write('\n' + ' | '.join(str(cell) for cell in row))

            # Summary
            total = len(invitations)
            pending = sum(1 for inv in invitations if inv.status == 'pending')
            valid = sum(1 for inv in invitations if inv.is_valid())

            self.stdout.write(f'\nTotal: {total} | Pending: {pending} | Valid: {valid}\n')
