"""
Models for multi-tenant SSO support.

Architecture:
    TenantSSOMixin  – abstract mixin; add to your app's Tenant/Organization model.
    Tenant          – built-in concrete tenant for standalone / simple use.
                      Swappable via DAMSSO_TENANT_MODEL (defaults to 'damsso.Tenant').
    TenantUser      – links users to tenants with role and external-SSO identity.
    SSOProvider     – OIDC / SAML configuration per tenant.
    TenantInvitation– invitation workflow for tenant membership.

To integrate with an existing Tenant model:
    1. Inherit TenantSSOMixin in your Tenant model.
    2. Set DAMSSO_TENANT_MODEL = 'myapp.MyTenant' in Django settings.
    3. Run migrations – damsso will use your model instead of its built-in Tenant.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from uuid_utils import uuid7 as uuid7_base

from .fields import EncryptedCharField, EncryptedTextField


def uuid7():
    """Generate a UUID7 and convert it to a standard uuid.UUID."""
    return uuid.UUID(str(uuid7_base()))


# ---------------------------------------------------------------------------
# Helper – resolves to the configured (or built-in) Tenant model
# ---------------------------------------------------------------------------

def get_tenant_model():
    """
    Return the Tenant model class configured by DAMSSO_TENANT_MODEL.

    Analogous to Django's get_user_model().  Call this at runtime (inside
    functions / methods), NOT at import time, to avoid circular imports.
    """
    from django.apps import apps
    model_string = getattr(settings, "DAMSSO_TENANT_MODEL", "damsso.Tenant")
    return apps.get_model(model_string)


# Resolve the model reference string once for FK field declarations.
# Using getattr with a default means the package works even when
# DAMSSO_TENANT_MODEL is not set (standalone mode → 'damsso.Tenant').
_TENANT_MODEL = getattr(settings, "DAMSSO_TENANT_MODEL", "damsso.Tenant")


# ---------------------------------------------------------------------------
# Try to import django-rls for Row Level Security support
# ---------------------------------------------------------------------------

try:
    from django_rls.models import RLSModel

    RLS_AVAILABLE = True
except ImportError:
    RLSModel = models.Model  # type: ignore[misc,assignment]
    RLS_AVAILABLE = False


# ---------------------------------------------------------------------------
# TenantSSOMixin – abstract model that adds SSO capabilities to any tenant
# ---------------------------------------------------------------------------

class TenantSSOMixin(models.Model):
    """
    Abstract mixin that adds SSO fields and helpers to any tenant model.

    Include this as a base class on your app's Tenant / Organization model:

        from damsso.models import TenantSSOMixin

        class Tenant(TenantSSOMixin, models.Model):
            slug = models.SlugField(primary_key=True)
            name = models.CharField(max_length=200)
            ...

    Then set in settings.py:
        DAMSSO_TENANT_MODEL = 'myapp.Tenant'

    Required fields on the concrete model (damsso's views depend on these):
        - ``slug``  – used in SSO URLs (e.g. /sso/login/<slug>/)
        - ``name``  – displayed in UI and emails
        - ``is_active`` – provided by this mixin; mark False to block SSO logins

    Optional / customisable:
        - ``domain`` – used by damsso diagnostics to verify email domains;
                       define on the concrete model if needed.
    """

    # SSO on/off switches
    sso_enabled = models.BooleanField(
        default=False,
        help_text=_("Enable SSO authentication for this tenant's users"),
    )
    sso_enforced = models.BooleanField(
        default=False,
        help_text=_("Enforce SSO — disable password login for tenant users"),
    )

    # Whether this tenant is active (gates all SSO operations)
    is_active = models.BooleanField(default=True)

    # Token for open / invite-link signups
    signup_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        help_text=_("Randomized token for tenant-specific signup URLs"),
    )

    # Arbitrary key-value bag for SSO provider metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # SSO helpers
    # ------------------------------------------------------------------

    def get_active_sso_provider(self):
        """Return the first active SSO provider for this tenant, or None."""
        return self.sso_providers.filter(is_active=True).first()  # type: ignore[attr-defined]

    def generate_signup_token(self):
        """Generate (or regenerate) the signup token and save it."""
        import secrets

        self.signup_token = secrets.token_urlsafe(32)
        self.save(update_fields=["signup_token"])
        return self.signup_token

    def get_signup_url(self, request=None):
        """Return the absolute signup URL for this tenant."""
        from django.urls import reverse

        if not self.signup_token:
            self.generate_signup_token()

        path = reverse("damsso:tenant_signup", args=[self.signup_token])
        if request:
            return request.build_absolute_uri(path)
        return path


# ---------------------------------------------------------------------------
# Tenant – built-in concrete model (swappable)
# ---------------------------------------------------------------------------

class Tenant(TenantSSOMixin, models.Model):
    """
    Built-in tenant model for standalone / simple deployments.

    For apps that already have their own Tenant model, set
    DAMSSO_TENANT_MODEL = 'myapp.MyTenant' instead of using this model.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    domain = models.CharField(
        max_length=255, blank=True, null=True,
        help_text=_("Primary domain for this tenant"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")
        swappable = "DAMSSO_TENANT_MODEL"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# TenantUser
# ---------------------------------------------------------------------------

class TenantUser(RLSModel):  # type: ignore[misc]
    """
    Links a user to a tenant with a role and optional external-SSO identity.

    Row Level Security (RLS): Uses database-level tenant isolation when
    django-rls + PostgreSQL are in use.
    """

    ROLE_CHOICES = [
        ("member", _("Member")),
        ("admin", _("Admin")),
        ("owner", _("Owner")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
    )
    tenant = models.ForeignKey(
        _TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_users",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    # External identity from SSO provider
    external_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text=_("User ID from external SSO provider"),
    )

    class Meta:
        unique_together = [["user", "tenant"]]
        ordering = ["-joined_at"]
        verbose_name = _("Tenant User")
        verbose_name_plural = _("Tenant Users")

    def __str__(self):
        return f"{self.user.email} - {self.tenant} ({self.role})"  # type: ignore[attr-defined]

    def is_tenant_admin(self):
        return self.role in ("admin", "owner")

    def get_all_tenants(self):
        """
        Return all tenants this user is a member of.

        Temporarily clears RLS context when django-rls is active so the
        cross-tenant query is not filtered down to a single tenant.
        """
        if RLS_AVAILABLE:
            try:
                from django_rls import set_tenant

                set_tenant(None)
                try:
                    tenant_pks = list(
                        TenantUser.objects.filter(user=self.user, is_active=True)
                        .values_list("tenant_id", flat=True)
                    )
                    return get_tenant_model().objects.filter(pk__in=tenant_pks)
                finally:
                    pass
            except ImportError:
                pass

        return get_tenant_model().objects.filter(
            tenant_users__user=self.user,
            tenant_users__is_active=True,
        )


# ---------------------------------------------------------------------------
# SSOProvider
# ---------------------------------------------------------------------------

class SSOProvider(RLSModel):  # type: ignore[misc]
    """
    OIDC or SAML SSO configuration for a tenant.

    Both protocol configs are stored together; ``protocol`` determines which
    is active.  Switching protocols does not discard the other config.

    Sensitive values (OIDC client secret, SAML X.509 cert) are encrypted at
    rest using Fernet symmetric encryption — requires FERNET_KEYS in settings.
    """

    PROTOCOL_CHOICES = [
        ("oidc", _("OpenID Connect (OIDC)")),
        ("saml", _("SAML 2.0")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        _TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="sso_providers",
    )
    name = models.CharField(max_length=255)
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        help_text=_("Active SSO protocol (OIDC or SAML)"),
    )
    is_active = models.BooleanField(default=False)
    is_tested = models.BooleanField(
        default=False,
        help_text=_("Has been successfully tested by an admin"),
    )

    # OIDC fields
    oidc_issuer = models.URLField(
        blank=True, null=True,
        help_text=_("OIDC Issuer URL (e.g. https://accounts.google.com)"),
    )
    oidc_client_id = models.CharField(max_length=255, blank=True)
    oidc_client_secret = EncryptedCharField(
        blank=True, null=True,
        editable=True,
        help_text=_("OIDC Client Secret (encrypted at rest)"),
    )
    oidc_authorization_endpoint = models.URLField(blank=True, null=True)
    oidc_token_endpoint = models.URLField(blank=True, null=True)
    oidc_userinfo_endpoint = models.URLField(blank=True, null=True)
    oidc_jwks_uri = models.URLField(blank=True, null=True)
    oidc_scopes = models.CharField(
        max_length=500, default="openid email profile",
        help_text=_("Space-separated list of OIDC scopes"),
    )

    # SAML fields
    saml_entity_id = models.CharField(max_length=500, blank=True, help_text=_("SAML Entity ID / Issuer"))
    saml_sso_url = models.URLField(blank=True, null=True, help_text=_("SAML Single Sign-On URL"))
    saml_slo_url = models.URLField(blank=True, null=True, help_text=_("SAML Single Logout URL (optional)"))
    saml_x509_cert = EncryptedTextField(
        blank=True, null=True,
        editable=True,
        help_text=_("X.509 Certificate for SAML (PEM format, encrypted at rest)"),
    )
    saml_attribute_mapping = models.JSONField(
        default=dict, blank=True,
        help_text=_("Mapping of SAML attributes to user fields"),
    )

    # Testing metadata
    last_tested_at = models.DateTimeField(blank=True, null=True)
    last_tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tested_sso_providers",
    )
    test_results = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("SSO Provider")
        verbose_name_plural = _("SSO Providers")

    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()}) — {self.tenant}"

    def clean(self):
        super().clean()
        if self.protocol == "oidc":
            if not self.oidc_issuer and not (self.oidc_authorization_endpoint and self.oidc_token_endpoint):
                raise ValidationError(
                    _("Either OIDC Issuer or both Authorization/Token endpoints are required")
                )
            for field in ("oidc_client_id", "oidc_client_secret"):
                if not getattr(self, field):
                    raise ValidationError({field: _("This field is required for OIDC")})
        elif self.protocol == "saml":
            for field in ("saml_entity_id", "saml_sso_url", "saml_x509_cert"):
                if not getattr(self, field):
                    raise ValidationError({field: _("This field is required for SAML")})

    def mark_as_tested(self, user, success=True, results=None):
        self.is_tested = success
        self.last_tested_at = timezone.now()
        self.last_tested_by = user
        if results:
            self.test_results = results
        self.save()


# ---------------------------------------------------------------------------
# TenantInvitation
# ---------------------------------------------------------------------------

class TenantInvitation(RLSModel):  # type: ignore[misc]
    """
    Invitation for a user to join a tenant.

    Row Level Security (RLS): Uses database-level tenant isolation when
    django-rls + PostgreSQL are in use.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("expired", _("Expired")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        _TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TenantUser.ROLE_CHOICES, default="member")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    token = models.CharField(max_length=255, unique=True, editable=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Tenant Invitation")
        verbose_name_plural = _("Tenant Invitations")

    def __str__(self):
        return f"Invitation for {self.email} to {self.tenant}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid7())
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.status == "pending" and self.expires_at > timezone.now()

    def accept(self, user):
        if not self.is_valid():
            raise ValidationError(_("This invitation is no longer valid"))

        tenant_user, created = TenantUser.objects.get_or_create(
            user=user,
            tenant=self.tenant,
            defaults={"role": self.role},
        )
        if not created and not tenant_user.is_active:
            tenant_user.is_active = True
            tenant_user.save()

        self.status = "accepted"
        self.accepted_at = timezone.now()
        self.save()
        return tenant_user
