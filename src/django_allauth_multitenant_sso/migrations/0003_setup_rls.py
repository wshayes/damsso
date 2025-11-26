"""
Migration to set up Row Level Security (RLS) policies for tenant isolation.

This migration requires PostgreSQL and the django-rls package.
It will be skipped automatically if using SQLite or other databases.
"""

from django.db import migrations


def setup_rls(apps, schema_editor):
    """
    Set up Row Level Security policies for tenant isolation.

    This creates PostgreSQL RLS policies that automatically filter
    all queries to only show data for the current tenant.
    """
    # Only run on PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return

    # Check if django-rls is available
    try:
        import django_rls  # noqa: F401
    except ImportError:
        # django-rls not installed, skip RLS setup
        return

    with schema_editor.connection.cursor() as cursor:
        # Enable RLS on tenant-scoped tables
        tables_and_fields = [
            ('django_allauth_multitenant_sso_tenantuser', 'tenant_id'),
            ('django_allauth_multitenant_sso_ssoprovider', 'tenant_id'),
            ('django_allauth_multitenant_sso_tenantinvitation', 'tenant_id'),
        ]

        for table_name, tenant_field in tables_and_fields:
            # Enable RLS on the table
            cursor.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")

            # Force RLS even for table owner (recommended for security)
            cursor.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;")

            # Create policy for tenant isolation
            # This policy allows all operations (SELECT, INSERT, UPDATE, DELETE)
            # but only for rows where tenant_id matches the current session's tenant
            policy_name = f"{table_name}_tenant_isolation"

            # Drop policy if it exists (for idempotency)
            cursor.execute(f"""
                DROP POLICY IF EXISTS {policy_name} ON {table_name};
            """)

            # Create the policy
            # The policy uses current_setting() to get the tenant_id from the session
            # If no tenant is set (e.g., admin access), it allows access to all rows
            cursor.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                USING (
                    {tenant_field}::text = current_setting('rls.tenant_id', true)
                    OR current_setting('rls.tenant_id', true) IS NULL
                );
            """)


def teardown_rls(apps, schema_editor):
    """
    Remove Row Level Security policies.

    This is the reverse migration that removes RLS policies.
    """
    # Only run on PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return

    try:
        import django_rls  # noqa: F401
    except ImportError:
        return

    with schema_editor.connection.cursor() as cursor:
        tables = [
            'django_allauth_multitenant_sso_tenantuser',
            'django_allauth_multitenant_sso_ssoprovider',
            'django_allauth_multitenant_sso_tenantinvitation',
        ]

        for table_name in tables:
            policy_name = f"{table_name}_tenant_isolation"

            # Drop the policy
            cursor.execute(f"""
                DROP POLICY IF EXISTS {policy_name} ON {table_name};
            """)

            # Disable RLS on the table
            cursor.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")


class Migration(migrations.Migration):
    """
    Migration to set up Row Level Security for multi-tenant isolation.
    """

    dependencies = [
        ('django_allauth_multitenant_sso', '0002_tenant_signup_token'),
    ]

    operations = [
        migrations.RunPython(
            setup_rls,
            reverse_code=teardown_rls,
        ),
    ]
