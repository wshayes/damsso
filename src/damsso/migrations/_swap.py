"""Helpers for swap-aware migrations.

When ``DAMSSO_TENANT_MODEL`` is swapped to a host-app model, damsso's
built-in ``damsso.Tenant`` table is not created and no migration in this
package may touch it. Use :func:`tenant_ops` to wrap CreateModel /
AlterField / AddField operations whose ``model_name`` is the built-in
Tenant.

Host apps may also need to inject extra migration-ordering constraints
(for example, to make sure a host-side tenant migration finishes before
damsso creates FK columns that reference it). They can do so by setting::

    DAMSSO_EXTRA_MIGRATION_DEPENDENCIES = {
        "0001_initial": [("tenants", "0002_subdomain_slug")],
    }
"""

from django.conf import settings


def is_standalone_tenant() -> bool:
    """True when ``DAMSSO_TENANT_MODEL`` resolves to the built-in model."""
    return getattr(settings, "DAMSSO_TENANT_MODEL", "damsso.Tenant") == "damsso.Tenant"


def tenant_ops(*ops):
    """Return ``ops`` in standalone mode; an empty list when Tenant is swapped."""
    return list(ops) if is_standalone_tenant() else []


def extra_dependencies(migration_name: str):
    """Return host-supplied extra dependencies for ``migration_name``."""
    extra = getattr(settings, "DAMSSO_EXTRA_MIGRATION_DEPENDENCIES", {}) or {}
    return list(extra.get(migration_name, []))
