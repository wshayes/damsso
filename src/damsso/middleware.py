"""
Middleware for multi-tenant SSO.
"""

from typing import Callable

from django.http import HttpRequest, HttpResponse

try:
    from django_rls import set_tenant
    RLS_AVAILABLE = True
except ImportError:
    RLS_AVAILABLE = False


class TenantRLSMiddleware:
    """
    Middleware to set the current tenant for Row Level Security (RLS).

    This middleware integrates with django-rls to provide database-level
    tenant isolation. It requires PostgreSQL and django_rls to be installed.

    The middleware reads the current tenant ID from the session and sets it
    as the RLS tenant context, ensuring that all database queries are automatically
    filtered to only include data belonging to the current tenant.

    Usage:
        Add to MIDDLEWARE in settings.py (after AuthenticationMiddleware):

        MIDDLEWARE = [
            ...
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'damsso.middleware.TenantRLSMiddleware',
            ...
        ]

    Requirements:
        - PostgreSQL database
        - django-rls package installed
        - Models configured with RLS policies

    Session Keys:
        - current_tenant_id: UUID of the current tenant (set during tenant login)
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

        if not RLS_AVAILABLE:
            import warnings
            warnings.warn(
                "django-rls is not installed. TenantRLSMiddleware will not provide "
                "database-level tenant isolation. Install django-rls and use PostgreSQL "
                "for production deployments requiring RLS.",
                RuntimeWarning
            )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only set RLS tenant if django-rls is available
        if RLS_AVAILABLE:
            # Get the current tenant ID from session
            tenant_id = request.session.get('current_tenant_id')

            if tenant_id:
                # Set the tenant for RLS (database-level isolation)
                set_tenant(tenant_id)
            else:
                # No tenant in session - clear RLS tenant (admin/superuser access)
                set_tenant(None)

        response = self.get_response(request)
        return response
