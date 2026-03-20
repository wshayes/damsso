"""
Views for the demo project.
"""

from django.views.generic import TemplateView

from damsso.models import TenantUser


class HomeView(TemplateView):
    """Home view with tenant information."""

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Get all tenant memberships for the user
            tenant_memberships = TenantUser.objects.filter(user=self.request.user, is_active=True).select_related(
                "tenant"
            )

            # Get tenants where user is admin
            admin_tenants = [membership.tenant for membership in tenant_memberships if membership.is_tenant_admin()]

            context["tenant_memberships"] = tenant_memberships
            context["admin_tenants"] = admin_tenants

        return context
