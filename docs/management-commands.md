# Management Commands

This document describes the management commands included with damsso.

## Send Pending Invitations

Send or resend invitation emails to users.

**Command:** `send_pending_invitations`

### Usage

```bash
# Send all pending invitations
python manage.py send_pending_invitations

# Send invitations for specific tenant
python manage.py send_pending_invitations --tenant-slug=acme

# Send invitation to specific email
python manage.py send_pending_invitations --email=user@example.com

# Dry run (show what would be sent without sending)
python manage.py send_pending_invitations --dry-run

# Resend all pending invitations (even if already sent)
python manage.py send_pending_invitations --resend
```

### Options

- `--tenant-slug`: Filter by tenant slug
- `--email`: Send invitation to specific email address
- `--dry-run`: Show what would be sent without actually sending
- `--resend`: Resend invitations even if they've already been sent

### Examples

```bash
# Send all pending invitations
python manage.py send_pending_invitations

# Send invitations for "acme" tenant only
python manage.py send_pending_invitations --tenant-slug=acme

# Send invitation to specific user
python manage.py send_pending_invitations --email=user@example.com

# See what would be sent
python manage.py send_pending_invitations --dry-run

# Resend all pending invitations
python manage.py send_pending_invitations --resend
```

### Output

The command will display:
- Number of invitations found
- Number of invitations sent
- Any errors encountered

Example output:
```
Found 5 pending invitations
Sending invitation to user1@example.com...
Sending invitation to user2@example.com...
...
Sent 5 invitations successfully
```

## Cleanup Invitations

Clean up expired or old invitations.

**Command:** `cleanup_invitations`

### Usage

```bash
# Mark expired invitations as expired
python manage.py cleanup_invitations

# Delete expired invitations
python manage.py cleanup_invitations --delete-expired

# Delete accepted invitations older than 30 days
python manage.py cleanup_invitations --delete-accepted --days=30

# Delete cancelled invitations
python manage.py cleanup_invitations --delete-cancelled

# Dry run (show what would be deleted)
python manage.py cleanup_invitations --delete-expired --dry-run
```

### Options

- `--delete-expired`: Delete expired invitations instead of just marking them
- `--delete-accepted`: Delete accepted invitations
- `--days`: Age threshold in days for deleting accepted invitations (default: 30)
- `--delete-cancelled`: Delete cancelled invitations
- `--dry-run`: Show what would be deleted without actually deleting

### Examples

```bash
# Mark expired invitations as expired
python manage.py cleanup_invitations

# Delete all expired invitations
python manage.py cleanup_invitations --delete-expired

# Delete accepted invitations older than 60 days
python manage.py cleanup_invitations --delete-accepted --days=60

# Delete cancelled invitations
python manage.py cleanup_invitations --delete-cancelled

# See what would be deleted
python manage.py cleanup_invitations --delete-expired --dry-run
```

### Output

The command will display:
- Number of invitations marked as expired
- Number of invitations deleted
- Breakdown by status

Example output:
```
Marked 3 invitations as expired
Deleted 5 expired invitations
Deleted 10 accepted invitations (older than 30 days)
Deleted 2 cancelled invitations
Total: 17 invitations processed
```

## List Invitations

View all invitations with various filters.

**Command:** `list_invitations`

### Usage

```bash
# List all invitations
python manage.py list_invitations

# Filter by tenant
python manage.py list_invitations --tenant-slug=acme

# Filter by status
python manage.py list_invitations --status=pending

# Show only expired invitations
python manage.py list_invitations --expired

# Output as JSON
python manage.py list_invitations --format=json

# Show detailed information
python manage.py list_invitations --verbose
```

### Options

- `--tenant-slug`: Filter by tenant slug
- `--status`: Filter by status (pending, accepted, expired, cancelled)
- `--expired`: Show only expired invitations
- `--format`: Output format (table, json, csv)
- `--verbose`: Show detailed information

### Examples

```bash
# List all invitations
python manage.py list_invitations

# List pending invitations for "acme" tenant
python manage.py list_invitations --tenant-slug=acme --status=pending

# List expired invitations
python manage.py list_invitations --expired

# Output as JSON
python manage.py list_invitations --format=json

# Show detailed information
python manage.py list_invitations --verbose
```

### Output

Default table format:
```
ID                                    Email              Tenant    Role    Status    Expires At
------------------------------------  -----------------  --------  ------  --------  -------------------
abc123...                            user1@example.com  acme      member  pending   2024-01-15 10:00:00
def456...                            user2@example.com  acme      admin   accepted  2024-01-10 10:00:00
```

JSON format:
```json
[
  {
    "id": "abc123...",
    "email": "user1@example.com",
    "tenant": "acme",
    "role": "member",
    "status": "pending",
    "expires_at": "2024-01-15T10:00:00Z"
  }
]
```

## Automation

### Cron Job Example

Set up a cron job to automatically send pending invitations:

```bash
# Send pending invitations daily at 9 AM
0 9 * * * cd /path/to/project && python manage.py send_pending_invitations
```

### Scheduled Cleanup

Set up a cron job to clean up old invitations:

```bash
# Clean up expired invitations weekly
0 2 * * 0 cd /path/to/project && python manage.py cleanup_invitations --delete-expired
```

### Using Celery

For better performance, you can create Celery tasks:

```python
# tasks.py
from celery import shared_task
from damsso.management.commands.send_pending_invitations import Command

@shared_task
def send_pending_invitations_task():
    command = Command()
    command.handle()
```

## Error Handling

All commands include error handling and will:
- Display clear error messages
- Continue processing other items if one fails
- Provide summary of successes and failures
- Exit with appropriate status codes

## Next Steps

- See the [Usage Guide](usage.md) for invitation workflows
- Review the [Models Reference](models.md) for TenantInvitation model
- Check the [Email Configuration Guide](email-configuration.md) for email setup

