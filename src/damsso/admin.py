"""
Admin interface for multi-tenant SSO models.

Registration is deferred to :func:`register_damsso_admin`, invoked from
:meth:`damsso.apps.DamssoConfig.ready`. This lets us gate which admins are
attached based on the host project's configuration:

* The bundled ``damsso.Tenant`` admin is only registered when
  ``DAMSSO_TENANT_MODEL == 'damsso.Tenant'`` (standalone mode). When the
  Tenant model is swapped, the host app owns admin registration for its
  own tenant model.
* The bundled ``TenantInvitation`` admin is only registered when
  ``DAMSSO_USE_BUILTIN_INVITATIONS`` is True (the default). Host apps
  that ship their own invitation flow can set it to False to hide
  damsso's admin entry without having to call ``admin.site.unregister``
  defensively.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import SSOProvider, TenantInvitation, TenantUser

# Organize admin sections
admin.site.index_template = "admin/index.html"


class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "domain", "sso_enabled", "sso_enforced", "is_active", "created_at"]
    list_filter = ["is_active", "sso_enabled", "sso_enforced", "created_at"]
    search_fields = ["name", "slug", "domain"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id", "signup_token", "signup_url", "created_at", "updated_at"]
    actions = ["generate_signup_token"]
    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "domain", "is_active")}),
        (_("SSO Settings"), {"fields": ("sso_enabled", "sso_enforced")}),
        (
            _("Signup Settings"),
            {
                "fields": ("signup_token", "signup_url"),
                "description": _("Share the signup URL to allow users to join this tenant."),
            },
        ),
        (_("Metadata"), {"fields": ("metadata", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")

    def signup_url(self, obj):
        """Display the signup URL for this tenant."""
        if not obj.signup_token:
            return format_html('<span style="color: #999;">No token generated</span>')

        from django.urls import reverse

        url = reverse("damsso:tenant_signup", args=[obj.signup_token])
        full_url = f"http://localhost:8000{url}"  # In production, use request.build_absolute_uri()
        return format_html(
            '<input type="text" readonly value="{}" style="width: 100%; font-family: monospace; font-size: 0.9em;" onclick="this.select();">',
            full_url,
        )

    signup_url.short_description = _("Signup URL")

    def generate_signup_token(self, request, queryset):
        """Admin action to generate/reset signup tokens."""
        count = 0
        for tenant in queryset:
            tenant.generate_signup_token()
            count += 1
        self.message_user(request, _("Generated signup tokens for {} tenants.").format(count))

    generate_signup_token.short_description = _("Generate/Reset signup token")


class TenantUserAdmin(admin.ModelAdmin):
    """
    Tenant User membership management.

    This shows which users belong to which tenants and their roles.
    For managing the actual user accounts (email, password, etc.), use the
    Authentication/Authorization > Users section or the tenant dashboard.
    """

    list_display = ["user_email", "tenant", "role", "is_active", "external_id", "joined_at"]
    list_filter = ["role", "is_active", "tenant", "joined_at"]
    search_fields = ["user__email", "tenant__name", "external_id"]
    readonly_fields = ["id", "joined_at"]
    autocomplete_fields = ["user", "tenant"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = _("User Email")
    user_email.admin_order_field = "user__email"

    class Meta:
        verbose_name = _("Tenant User")
        verbose_name_plural = _("Tenant Users")


class SSOProviderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "tenant",
        "protocol",
        "is_active",
        "is_tested",
        "status_indicator",
        "last_tested_at",
        "created_at",
    ]
    list_filter = ["protocol", "is_active", "is_tested", "created_at"]
    search_fields = ["name", "tenant__name", "oidc_client_id", "saml_entity_id"]
    readonly_fields = [
        "id",
        "is_tested",
        "last_tested_at",
        "last_tested_by",
        "test_results",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["tenant"]

    fieldsets = (
        (None, {"fields": ("id", "tenant", "name", "protocol", "is_active")}),
        (
            _("OIDC Configuration"),
            {
                "fields": (
                    "oidc_issuer",
                    "oidc_client_id",
                    "oidc_client_secret",
                    "oidc_authorization_endpoint",
                    "oidc_token_endpoint",
                    "oidc_userinfo_endpoint",
                    "oidc_jwks_uri",
                    "oidc_scopes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("SAML Configuration"),
            {
                "fields": (
                    "saml_entity_id",
                    "saml_sso_url",
                    "saml_slo_url",
                    "saml_x509_cert",
                    "saml_attribute_mapping",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Testing Information"),
            {"fields": ("is_tested", "last_tested_at", "last_tested_by", "test_results"), "classes": ("collapse",)},
        ),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def status_indicator(self, obj):
        if obj.is_active and obj.is_tested:
            color = "green"
            text = "Active & Tested"
        elif obj.is_active:
            color = "orange"
            text = "Active (Not Tested)"
        elif obj.is_tested:
            color = "blue"
            text = "Inactive (Tested)"
        else:
            color = "red"
            text = "Inactive"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)

    status_indicator.short_description = _("Status")


class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "tenant", "role", "status", "invited_by", "created_at", "expires_at"]
    list_filter = ["status", "role", "created_at", "expires_at"]
    search_fields = ["email", "tenant__name", "invited_by__email"]
    readonly_fields = ["id", "token", "created_at", "accepted_at"]
    autocomplete_fields = ["tenant", "invited_by"]

    fieldsets = (
        (None, {"fields": ("id", "tenant", "email", "role", "invited_by")}),
        (_("Status"), {"fields": ("status", "token", "expires_at", "accepted_at")}),
        (_("Timestamps"), {"fields": ("created_at",)}),
    )


def register_damsso_admin():
    """
    Register damsso's admin classes, honoring host-app opt-outs.

    Idempotent: skips any model whose admin is already registered (so host
    apps can register their own custom admin first).
    """
    from django.conf import settings

    from .models import get_tenant_model

    # TenantUser and SSOProvider exist in both standalone and swap modes.
    if not admin.site.is_registered(TenantUser):
        admin.site.register(TenantUser, TenantUserAdmin)
    if not admin.site.is_registered(SSOProvider):
        admin.site.register(SSOProvider, SSOProviderAdmin)

    # Tenant admin: only when using the built-in concrete model.
    tenant_model = get_tenant_model()
    import damsso.models as damsso_models
    if tenant_model is damsso_models.Tenant and not admin.site.is_registered(tenant_model):
        admin.site.register(tenant_model, TenantAdmin)

    # TenantInvitation admin: host can opt out via DAMSSO_USE_BUILTIN_INVITATIONS = False.
    use_invitations = getattr(settings, "DAMSSO_USE_BUILTIN_INVITATIONS", True)
    if use_invitations and not admin.site.is_registered(TenantInvitation):
        admin.site.register(TenantInvitation, TenantInvitationAdmin)


def register_damsso_tenant_admin():
    """Deprecated alias for :func:`register_damsso_admin`. Kept for back-compat."""
    register_damsso_admin()
