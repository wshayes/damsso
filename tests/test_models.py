"""
Tests for models in django-allauth-multitenant-sso.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django_allauth_multitenant_sso.models import (
    Tenant, TenantUser, SSOProvider, TenantInvitation
)

User = get_user_model()


class TestTenant:
    """Tests for Tenant model."""

    def test_create_tenant(self, tenant):
        """Test creating a tenant."""
        assert tenant.name == 'Test Tenant'
        assert tenant.slug == 'test-tenant'
        assert tenant.domain == 'test.example.com'
        assert tenant.is_active is True
        assert tenant.sso_enabled is False
        assert tenant.sso_enforced is False

    def test_tenant_str(self, tenant):
        """Test tenant string representation."""
        assert str(tenant) == 'Test Tenant'

    def test_tenant_ordering(self, tenant, another_tenant):
        """Test tenants are ordered by name."""
        tenants = list(Tenant.objects.all())
        assert tenants[0] == another_tenant  # 'Another Tenant' comes first
        assert tenants[1] == tenant  # 'Test Tenant' comes second

    def test_get_active_sso_provider_with_provider(self, tenant, oidc_provider):
        """Test getting active SSO provider."""
        provider = tenant.get_active_sso_provider()
        assert provider == oidc_provider

    def test_get_active_sso_provider_without_provider(self, tenant):
        """Test getting active SSO provider when none exists."""
        provider = tenant.get_active_sso_provider()
        assert provider is None

    def test_tenant_unique_name(self, tenant):
        """Test tenant name must be unique."""
        with pytest.raises(Exception):  # IntegrityError
            Tenant.objects.create(
                name='Test Tenant',
                slug='different-slug'
            )

    def test_tenant_unique_slug(self, tenant):
        """Test tenant slug must be unique."""
        with pytest.raises(Exception):  # IntegrityError
            Tenant.objects.create(
                name='Different Tenant',
                slug='test-tenant'
            )


class TestTenantUser:
    """Tests for TenantUser model."""

    def test_create_tenant_user(self, tenant_user, user, tenant):
        """Test creating a tenant user."""
        assert tenant_user.user == user
        assert tenant_user.tenant == tenant
        assert tenant_user.role == 'member'
        assert tenant_user.is_active is True

    def test_tenant_user_str(self, tenant_user):
        """Test tenant user string representation."""
        assert str(tenant_user) == 'testuser@example.com - Test Tenant (member)'

    def test_is_tenant_admin_member(self, tenant_user):
        """Test is_tenant_admin for member role."""
        assert tenant_user.is_tenant_admin() is False

    def test_is_tenant_admin_admin(self, tenant_admin):
        """Test is_tenant_admin for admin role."""
        assert tenant_admin.is_tenant_admin() is True

    def test_is_tenant_admin_owner(self, tenant_owner):
        """Test is_tenant_admin for owner role."""
        assert tenant_owner.is_tenant_admin() is True

    def test_tenant_user_unique_constraint(self, user, tenant):
        """Test user cannot be added to same tenant twice."""
        TenantUser.objects.create(user=user, tenant=tenant, role='member')
        with pytest.raises(Exception):  # IntegrityError
            TenantUser.objects.create(user=user, tenant=tenant, role='admin')

    def test_tenant_user_multiple_tenants(self, user, tenant, another_tenant):
        """Test user can belong to multiple tenants."""
        tu1 = TenantUser.objects.create(user=user, tenant=tenant, role='member')
        tu2 = TenantUser.objects.create(user=user, tenant=another_tenant, role='admin')
        assert tu1.tenant == tenant
        assert tu2.tenant == another_tenant

    def test_tenant_user_external_id(self, user, tenant):
        """Test tenant user with external ID."""
        tu = TenantUser.objects.create(
            user=user,
            tenant=tenant,
            role='member',
            external_id='external-123'
        )
        assert tu.external_id == 'external-123'


class TestSSOProvider:
    """Tests for SSOProvider model."""

    def test_create_oidc_provider(self, oidc_provider, tenant):
        """Test creating an OIDC provider."""
        assert oidc_provider.tenant == tenant
        assert oidc_provider.name == 'Test OIDC Provider'
        assert oidc_provider.protocol == 'oidc'
        assert oidc_provider.oidc_issuer == 'https://accounts.google.com'
        assert oidc_provider.oidc_client_id == 'test-client-id'
        assert oidc_provider.oidc_client_secret == 'test-client-secret'
        assert oidc_provider.is_active is True
        assert oidc_provider.is_tested is False

    def test_create_saml_provider(self, saml_provider, tenant):
        """Test creating a SAML provider."""
        assert saml_provider.tenant == tenant
        assert saml_provider.name == 'Test SAML Provider'
        assert saml_provider.protocol == 'saml'
        assert saml_provider.saml_entity_id == 'https://idp.example.com'
        assert saml_provider.saml_sso_url == 'https://idp.example.com/sso'
        assert 'BEGIN CERTIFICATE' in saml_provider.saml_x509_cert
        assert saml_provider.saml_attribute_mapping == {
            'email': 'email',
            'firstName': 'first_name',
            'lastName': 'last_name'
        }

    def test_sso_provider_str(self, oidc_provider):
        """Test SSO provider string representation."""
        assert 'Test OIDC Provider' in str(oidc_provider)
        assert 'OpenID Connect' in str(oidc_provider)
        assert 'Test Tenant' in str(oidc_provider)

    def test_oidc_provider_validation_missing_client_id(self, tenant):
        """Test OIDC provider validation fails without client ID."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid OIDC',
            protocol='oidc',
            oidc_issuer='https://accounts.google.com',
            oidc_client_secret='secret'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_oidc_provider_validation_missing_client_secret(self, tenant):
        """Test OIDC provider validation fails without client secret."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid OIDC',
            protocol='oidc',
            oidc_issuer='https://accounts.google.com',
            oidc_client_id='client-id'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_oidc_provider_validation_missing_issuer_and_endpoints(self, tenant):
        """Test OIDC provider validation fails without issuer or endpoints."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid OIDC',
            protocol='oidc',
            oidc_client_id='client-id',
            oidc_client_secret='secret'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_oidc_provider_validation_with_endpoints(self, tenant):
        """Test OIDC provider validation passes with endpoints."""
        provider = SSOProvider(
            tenant=tenant,
            name='Valid OIDC',
            protocol='oidc',
            oidc_client_id='client-id',
            oidc_client_secret='secret',
            oidc_authorization_endpoint='https://provider.com/auth',
            oidc_token_endpoint='https://provider.com/token'
        )
        provider.full_clean()  # Should not raise

    def test_saml_provider_validation_missing_entity_id(self, tenant):
        """Test SAML provider validation fails without entity ID."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_sso_url='https://idp.example.com/sso',
            saml_x509_cert='cert'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_saml_provider_validation_missing_sso_url(self, tenant):
        """Test SAML provider validation fails without SSO URL."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_entity_id='https://idp.example.com',
            saml_x509_cert='cert'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_saml_provider_validation_missing_cert(self, tenant):
        """Test SAML provider validation fails without certificate."""
        provider = SSOProvider(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_entity_id='https://idp.example.com',
            saml_sso_url='https://idp.example.com/sso'
        )
        with pytest.raises(ValidationError):
            provider.full_clean()

    def test_mark_as_tested(self, oidc_provider, user):
        """Test marking provider as tested."""
        test_results = {
            'success': True,
            'message': 'Test successful'
        }
        oidc_provider.mark_as_tested(user, success=True, results=test_results)

        assert oidc_provider.is_tested is True
        assert oidc_provider.last_tested_by == user
        assert oidc_provider.last_tested_at is not None
        assert oidc_provider.test_results == test_results

    def test_mark_as_tested_failed(self, oidc_provider, user):
        """Test marking provider as failed test."""
        oidc_provider.mark_as_tested(user, success=False)
        assert oidc_provider.is_tested is False
        assert oidc_provider.last_tested_by == user


class TestTenantInvitation:
    """Tests for TenantInvitation model."""

    def test_create_invitation(self, invitation, user, tenant):
        """Test creating an invitation."""
        assert invitation.tenant == tenant
        assert invitation.email == 'invited@example.com'
        assert invitation.role == 'member'
        assert invitation.invited_by == user
        assert invitation.status == 'pending'
        assert invitation.token is not None
        assert len(invitation.token) == 32  # UUID hex is 32 chars
        assert invitation.expires_at is not None

    def test_invitation_auto_generates_token(self, user, tenant):
        """Test invitation auto-generates token on save."""
        invitation = TenantInvitation(
            tenant=tenant,
            email='test@example.com',
            invited_by=user
        )
        assert invitation.token is None or invitation.token == ''
        invitation.save()
        assert invitation.token is not None
        assert len(invitation.token) == 32

    def test_invitation_auto_sets_expiration(self, user, tenant):
        """Test invitation auto-sets expiration date."""
        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email='test@example.com',
            invited_by=user
        )
        # Should expire in 7 days
        expected_expiry = timezone.now() + timedelta(days=7)
        time_diff = abs((invitation.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_invitation_str(self, invitation):
        """Test invitation string representation."""
        assert str(invitation) == 'Invitation for invited@example.com to Test Tenant'

    def test_is_valid_pending_not_expired(self, invitation):
        """Test invitation is valid when pending and not expired."""
        assert invitation.is_valid() is True

    def test_is_valid_expired(self, expired_invitation):
        """Test invitation is not valid when expired."""
        assert expired_invitation.is_valid() is False

    def test_is_valid_accepted(self, invitation, user):
        """Test invitation is not valid when already accepted."""
        invitation.status = 'accepted'
        invitation.save()
        assert invitation.is_valid() is False

    def test_accept_invitation_creates_tenant_user(self, invitation, another_user):
        """Test accepting invitation creates TenantUser."""
        # Create user with matching email
        user = User.objects.create_user(
            username='invited',
            email='invited@example.com',
            password='pass123'
        )

        tenant_user = invitation.accept(user)
        assert tenant_user.user == user
        assert tenant_user.tenant == invitation.tenant
        assert tenant_user.role == invitation.role
        assert invitation.status == 'accepted'
        assert invitation.accepted_at is not None

    def test_accept_invitation_reactivates_inactive_user(self, invitation, user, tenant):
        """Test accepting invitation reactivates inactive tenant user."""
        # Create user with matching email
        invited_user = User.objects.create_user(
            username='invited',
            email='invited@example.com',
            password='pass123'
        )

        # Create inactive tenant user
        inactive_tu = TenantUser.objects.create(
            user=invited_user,
            tenant=tenant,
            role='member',
            is_active=False
        )

        tenant_user = invitation.accept(invited_user)
        inactive_tu.refresh_from_db()
        assert inactive_tu.is_active is True

    def test_accept_expired_invitation_raises_error(self, expired_invitation, user):
        """Test accepting expired invitation raises ValidationError."""
        with pytest.raises(ValidationError):
            expired_invitation.accept(user)

    def test_accept_cancelled_invitation_raises_error(self, invitation, user):
        """Test accepting cancelled invitation raises ValidationError."""
        invitation.status = 'cancelled'
        invitation.save()
        with pytest.raises(ValidationError):
            invitation.accept(user)
