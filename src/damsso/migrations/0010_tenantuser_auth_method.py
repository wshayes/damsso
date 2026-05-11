# Generated for tenant SSO routing — adds per-membership auth_method.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('damsso', '0009_alter_ssoprovider_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantuser',
            name='auth_method',
            field=models.CharField(
                choices=[('sso', 'Tenant SSO'), ('local', 'Local password')],
                default='sso',
                help_text=(
                    'How this membership authenticates: tenant SSO or local password. '
                    'Overrides tenant-level SSO enforcement when set to local.'
                ),
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='tenantinvitation',
            name='auth_method',
            field=models.CharField(
                choices=[('sso', 'Tenant SSO'), ('local', 'Local password')],
                default='sso',
                help_text=(
                    'Authentication method to apply to the TenantUser when this '
                    'invitation is accepted.'
                ),
                max_length=10,
            ),
        ),
    ]
