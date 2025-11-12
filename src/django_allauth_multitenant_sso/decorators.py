"""
Decorators for multi-tenant access control.
"""
from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Tenant, TenantUser


def tenant_member_required(view_func):
    """
    Decorator to ensure user is a member of the tenant.
    """
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        try:
            tenant_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                is_active=True
            )
            # Store tenant user in request for easy access
            request.tenant_user = tenant_user
            request.tenant = tenant

        except TenantUser.DoesNotExist:
            messages.error(
                request,
                _("You do not have access to this organization.")
            )
            return redirect('account_login')

        return view_func(request, tenant_slug, *args, **kwargs)

    return wrapper


def tenant_admin_required(view_func):
    """
    Decorator to ensure user is an admin or owner of the tenant.
    """
    @wraps(view_func)
    def wrapper(request, tenant_slug, *args, **kwargs):
        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        try:
            tenant_user = TenantUser.objects.get(
                user=request.user,
                tenant=tenant,
                is_active=True
            )

            if not tenant_user.is_tenant_admin():
                messages.error(
                    request,
                    _("You do not have admin access to this organization.")
                )
                return redirect('account_login')

            # Store tenant user in request for easy access
            request.tenant_user = tenant_user
            request.tenant = tenant

        except TenantUser.DoesNotExist:
            messages.error(
                request,
                _("You do not have access to this organization.")
            )
            return redirect('account_login')

        return view_func(request, tenant_slug, *args, **kwargs)

    return wrapper
