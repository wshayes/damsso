"""
Migration to set up Row Level Security (RLS) policies for tenant isolation.

This migration requires PostgreSQL and the django-rls package.
It is skipped automatically when:
  * the database is not PostgreSQL, or
  * django-rls is not installed, or
  * ``DAMSSO_ENABLE_RLS`` is set to False.

Host apps that already manage their own RLS can disable this migration's
DDL by setting ``DAMSSO_ENABLE_RLS = False``. The policy's admin-bypass
predicate can also be overridden by setting
``DAMSSO_RLS_BYPASS_PREDICATE`` to a SQL fragment (default:
``current_setting('rls.tenant_id', true) IS NULL``).
"""

from django.conf import settings
from django.db import migrations

from ._swap import extra_dependencies

DEFAULT_BYPASS_PREDICATE = "current_setting('rls.tenant_id', true) IS NULL"


def _rls_enabled() -> bool:
    return bool(getattr(settings, "DAMSSO_ENABLE_RLS", True))


def _bypass_predicate() -> str:
    return getattr(settings, "DAMSSO_RLS_BYPASS_PREDICATE", DEFAULT_BYPASS_PREDICATE)


def setup_rls(apps, schema_editor):
    """
    Set up Row Level Security policies for tenant isolation.

    This creates PostgreSQL RLS policies that automatically filter
    all queries to only show data for the current tenant.
    """
    # Honor the host opt-out before touching anything.
    if not _rls_enabled():
        return

    # Only run on PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return

    # Check if django-rls is available
    try:
        import django_rls  # noqa: F401
    except ImportError:
        # django-rls not installed, skip RLS setup
        return

    bypass = _bypass_predicate()

    with schema_editor.connection.cursor() as cursor:
        # Enable RLS on tenant-scoped tables
        tables_and_fields = [
            ('damsso_tenantuser', 'tenant_id'),
            ('damsso_ssoprovider', 'tenant_id'),
            ('damsso_tenantinvitation', 'tenant_id'),
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

            # Create the policy. ``bypass`` is a SQL fragment supplied by the
            # host (or the default) that determines when admin/no-tenant
            # contexts may see all rows.
            cursor.execute(f"""
                CREATE POLICY {policy_name} ON {table_name}
                USING (
                    {tenant_field}::text = current_setting('rls.tenant_id', true)
                    OR ({bypass})
                );
            """)


def teardown_rls(apps, schema_editor):
    """
    Remove Row Level Security policies.

    This is the reverse migration that removes RLS policies.
    """
    if not _rls_enabled():
        return

    # Only run on PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return

    try:
        import django_rls  # noqa: F401
    except ImportError:
        return

    with schema_editor.connection.cursor() as cursor:
        tables = [
            'damsso_tenantuser',
            'damsso_ssoprovider',
            'damsso_tenantinvitation',
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
        ('damsso', '0002_tenant_signup_token'),
        # Host apps can inject ordering constraints (e.g. their tenant's
        # slug-PK migration must finish first) via
        # DAMSSO_EXTRA_MIGRATION_DEPENDENCIES["0003_setup_rls"].
        *extra_dependencies("0003_setup_rls"),
    ]

    operations = [
        migrations.RunPython(
            setup_rls,
            reverse_code=teardown_rls,
        ),
    ]
