"""
Models for multi-tenant SSO support.
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
    """Generate a UUID7 and convert it to standard UUID."""
    return uuid.UUID(str(uuid7_base()))

# Try to import django-rls for Row Level Security support
try:
    from django_rls.models import RLSModel

    RLS_AVAILABLE = True
except ImportError:
    # Fallback to regular Model if django-rls is not installed
    RLSModel = models.Model
    RLS_AVAILABLE = False


class Tenant(models.Model):
    """
    Represents a tenant organization that can have multiple users and SSO configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SSO settings
    sso_enabled = models.BooleanField(default=False, help_text=_("Enable SSO authentication for this tenant's users"))  # type: ignore[arg-type]
    sso_enforced = models.BooleanField(
        default=False,
        help_text=_("Enforce SSO authentication (disable password login)"),  # type: ignore[arg-type]
    )

    # Additional tenant metadata
    domain = models.CharField(max_length=255, blank=True, null=True, help_text=_("Primary domain for this tenant"))
    metadata = models.JSONField(default=dict, blank=True)

    # Signup token for public signup URLs
    signup_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        unique=True,
        help_text=_("Randomized token for tenant-specific signup URLs"),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")

    def __str__(self):
        return self.name

    def get_active_sso_provider(self):
        """Get the active SSO provider for this tenant."""
        return self.sso_providers.filter(is_active=True).first()  # type: ignore[attr-defined]

    def generate_signup_token(self):
        """Generate a new randomized signup token for this tenant."""
        import secrets

        self.signup_token = secrets.token_urlsafe(32)
        self.save(update_fields=["signup_token"])
        return self.signup_token

    def get_signup_url(self, request=None):
        """Get the signup URL for this tenant."""
        from django.urls import reverse

        if not self.signup_token:
            self.generate_signup_token()

        if request:
            return request.build_absolute_uri(
                reverse("allauth_multitenant_sso:tenant_signup", args=[self.signup_token])
            )
        return reverse("allauth_multitenant_sso:tenant_signup", args=[self.signup_token])


class TenantUser(RLSModel):  # type: ignore[misc]
    """
    Links users to tenants and stores tenant-specific user information.

    Row Level Security (RLS): This model uses database-level tenant isolation
    when django-rls is installed and PostgreSQL is used. Each row is automatically
    filtered to only be accessible when the current tenant matches the row's tenant.
    """

    ROLE_CHOICES = [
        ("member", _("Member")),
        ("admin", _("Admin")),
        ("owner", _("Owner")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tenant_users")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    # External identity info (from SSO)
    external_id = models.CharField(
        max_length=255, blank=True, null=True, help_text=_("User ID from external SSO provider")
    )

    class Meta:
        unique_together = [["user", "tenant"]]
        ordering = ["-joined_at"]
        verbose_name = _("Tenant User")
        verbose_name_plural = _("Tenant Users")

    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.role})"  # type: ignore[attr-defined]

    def is_tenant_admin(self):
        """Check if user has admin or owner role."""
        return self.role in ["admin", "owner"]

    def get_all_tenants(self):
        """
        Get all tenants for the user.

        Note: When RLS is enabled, this method temporarily clears the RLS tenant context
        to query across all tenant memberships. This is safe because we're only reading
        tenant IDs that the user is already a member of.
        """
        if RLS_AVAILABLE:
            try:
                from django_rls import set_tenant

                # Temporarily clear RLS to see all tenant memberships for this user
                # This is necessary because RLS would filter TenantUser to only show
                # memberships for the current tenant, but we need to see all tenants
                # the user belongs to
                set_tenant(None)
                try:
                    # Query TenantUser directly to get all tenant IDs for this user
                    tenant_ids = list(
                        TenantUser.objects.filter(user=self.user, is_active=True).values_list("tenant_id", flat=True)
                    )  # type: ignore[attr-defined]
                    # Query Tenant (no RLS) with those IDs
                    return Tenant.objects.filter(id__in=tenant_ids)
                finally:
                    # Clear tenant context - middleware will restore it on next request
                    # Note: We don't restore the previous tenant here to avoid side effects
                    # The middleware will set it correctly based on the session
                    pass
            except ImportError:
                pass
        # Fallback: direct query when RLS is not available
        return Tenant.objects.filter(tenant_users__user=self.user, tenant_users__is_active=True)  # type: ignore[attr-defined]


class SSOProvider(RLSModel):  # type: ignore[misc]
    """
    Stores SSO provider configuration for a tenant.

    This model can store both OIDC and SAML configurations. The 'protocol' field
    determines which configuration is currently active. Both OIDC and SAML fields
    are stored independently and switching between protocols does not lose data.

    Row Level Security (RLS): This model uses database-level tenant isolation
    when django-rls is installed and PostgreSQL is used. Each SSO provider is
    automatically filtered to only be accessible when the current tenant matches.
    """

    PROTOCOL_CHOICES = [
        ("oidc", _("OpenID Connect (OIDC)")),
        ("saml", _("SAML 2.0")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sso_providers")
    name = models.CharField(max_length=255)
    protocol = models.CharField(
        max_length=10,
        choices=PROTOCOL_CHOICES,
        help_text=_("Which SSO protocol is currently active (OIDC or SAML)"),
    )
    is_active = models.BooleanField(default=False)
    is_tested = models.BooleanField(default=False, help_text=_(("Has been successfully tested by admin")))  # type: ignore[arg-type]

    # OIDC Configuration (only used when protocol='oidc')
    # These fields are preserved when switching to SAML
    oidc_issuer = models.URLField(
        blank=True, null=True, help_text=_("OIDC Issuer URL (e.g., https://accounts.google.com)")
    )
    oidc_client_id = models.CharField(max_length=255, blank=True)
    oidc_client_secret = EncryptedCharField(
        max_length=500, blank=True, null=True, help_text=_("OIDC Client Secret (encrypted at rest)")
    )
    oidc_authorization_endpoint = models.URLField(blank=True, null=True)
    oidc_token_endpoint = models.URLField(blank=True, null=True)
    oidc_userinfo_endpoint = models.URLField(blank=True, null=True)
    oidc_jwks_uri = models.URLField(blank=True, null=True)
    oidc_scopes = models.CharField(
        max_length=500, default="openid email profile", help_text=_("Space-separated list of scopes")
    )

    # SAML Configuration (only used when protocol='saml')
    # These fields are preserved when switching to OIDC
    saml_entity_id = models.CharField(max_length=500, blank=True, help_text=_("SAML Entity ID / Issuer"))
    saml_sso_url = models.URLField(blank=True, null=True, help_text=_("SAML Single Sign-On URL"))
    saml_slo_url = models.URLField(blank=True, null=True, help_text=_("SAML Single Logout URL (optional)"))
    saml_x509_cert = EncryptedTextField(
        blank=True, null=True, help_text=_("X.509 Certificate for SAML (PEM format, encrypted at rest)")
    )
    saml_attribute_mapping = models.JSONField(
        default=dict, blank=True, help_text=_("Mapping of SAML attributes to user fields")
    )

    # Testing and metadata
    last_tested_at = models.DateTimeField(blank=True, null=True)
    last_tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tested_sso_providers"
    )
    test_results = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("SSO Provider")
        verbose_name_plural = _("SSO Providers")

    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()}) - {self.tenant.name}"

    def clean(self):
        """Validate that required fields are present based on protocol."""
        super().clean()
        if self.protocol == "oidc":
            required_fields = ["oidc_client_id", "oidc_client_secret"]
            if not self.oidc_issuer and not (self.oidc_authorization_endpoint and self.oidc_token_endpoint):
                raise ValidationError(_("Either OIDC Issuer or Authorization/Token endpoints are required"))  # type: ignore[arg-type]
            for field in required_fields:
                if not getattr(self, field):
                    raise ValidationError({field: _("This field is required for OIDC")})  # type: ignore[arg-type]

        elif self.protocol == "saml":
            required_fields = ["saml_entity_id", "saml_sso_url", "saml_x509_cert"]
            for field in required_fields:
                if not getattr(self, field):
                    raise ValidationError({field: _("This field is required for SAML")})  # type: ignore[arg-type]

    def mark_as_tested(self, user, success=True, results=None):
        """Mark provider as tested with results."""
        self.is_tested = success
        self.last_tested_at = timezone.now()
        self.last_tested_by = user
        if results:
            self.test_results = results
        self.save()


class TenantInvitation(RLSModel):  # type: ignore[misc]
    """
    Invitations for users to join a tenant.

    Row Level Security (RLS): This model uses database-level tenant isolation
    when django-rls is installed and PostgreSQL is used. Each invitation is
    automatically filtered to only be accessible when the current tenant matches.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("expired", _("Expired")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TenantUser.ROLE_CHOICES, default="member")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
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
        return f"Invitation for {self.email} to {self.tenant.name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid7())
        if not self.expires_at:
            from datetime import timedelta

            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if invitation is still valid."""
        return self.status == "pending" and self.expires_at > timezone.now()

    def accept(self, user):
        """Accept the invitation for a user."""
        if not self.is_valid():
            raise ValidationError(_("This invitation is no longer valid"))  # type: ignore[arg-type]

        # Create or update TenantUser
        tenant_user, created = TenantUser.objects.get_or_create(
            user=user, tenant=self.tenant, defaults={"role": self.role}
        )

        if not created and not tenant_user.is_active:
            tenant_user.is_active = True
            tenant_user.save()

        self.status = "accepted"
        self.accepted_at = timezone.now()
        self.save()

        return tenant_user
