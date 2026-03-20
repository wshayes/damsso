"""
Tests for forms in damsso.
"""
import pytest
from damsso.forms import (
    TenantForm,
    SSOProviderForm,
    OIDCProviderForm,
    SAMLProviderForm,
    TenantInvitationForm
)
from damsso.models import TenantUser, TenantInvitation


class TestTenantForm:
    """Tests for TenantForm."""

    def test_valid_form(self):
        """Test form with valid data."""
        form_data = {
            'name': 'New Tenant',
            'slug': 'new-tenant',
            'domain': 'new.example.com',
            'is_active': True
        }
        form = TenantForm(data=form_data)
        assert form.is_valid()

    def test_form_saves(self):
        """Test form saves tenant correctly."""
        form_data = {
            'name': 'New Tenant',
            'slug': 'new-tenant',
            'domain': 'new.example.com',
            'is_active': True
        }
        form = TenantForm(data=form_data)
        assert form.is_valid()
        tenant = form.save()
        assert tenant.name == 'New Tenant'
        assert tenant.slug == 'new-tenant'

    def test_invalid_form_missing_name(self):
        """Test form is invalid without name."""
        form_data = {
            'slug': 'test-slug',
        }
        form = TenantForm(data=form_data)
        assert not form.is_valid()
        assert 'name' in form.errors


class TestSSOProviderForm:
    """Tests for SSOProviderForm."""

    def test_form_has_correct_fields(self):
        """Test form has name and protocol fields."""
        form = SSOProviderForm()
        assert 'name' in form.fields
        assert 'protocol' in form.fields
        assert len(form.fields) == 2


class TestOIDCProviderForm:
    """Tests for OIDCProviderForm."""

    def test_valid_form_with_issuer(self):
        """Test form with issuer discovery."""
        form_data = {
            'name': 'Google OIDC',
            'oidc_issuer': 'https://accounts.google.com',
            'oidc_client_id': 'client-123',
            'oidc_client_secret': 'secret-456',
            'oidc_scopes': 'openid email profile'
        }
        form = OIDCProviderForm(data=form_data)
        assert form.is_valid()

    def test_valid_form_with_endpoints(self):
        """Test form with manual endpoint configuration."""
        form_data = {
            'name': 'Custom OIDC',
            'oidc_client_id': 'client-123',
            'oidc_client_secret': 'secret-456',
            'oidc_authorization_endpoint': 'https://provider.com/auth',
            'oidc_token_endpoint': 'https://provider.com/token',
            'oidc_userinfo_endpoint': 'https://provider.com/userinfo',
            'oidc_scopes': 'openid email'
        }
        form = OIDCProviderForm(data=form_data)
        assert form.is_valid()


class TestSAMLProviderForm:
    """Tests for SAMLProviderForm."""

    def test_valid_form(self):
        """Test form with valid SAML data."""
        form_data = {
            'name': 'Okta SAML',
            'saml_entity_id': 'https://idp.example.com',
            'saml_sso_url': 'https://idp.example.com/sso',
            'saml_x509_cert': '-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----',
            'saml_attribute_mapping': '{"email": "email"}'
        }
        form = SAMLProviderForm(data=form_data)
        assert form.is_valid()

    def test_form_with_slo_url(self):
        """Test form with optional SLO URL."""
        form_data = {
            'name': 'Okta SAML',
            'saml_entity_id': 'https://idp.example.com',
            'saml_sso_url': 'https://idp.example.com/sso',
            'saml_slo_url': 'https://idp.example.com/slo',
            'saml_x509_cert': '-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----',
        }
        form = SAMLProviderForm(data=form_data)
        assert form.is_valid()


class TestTenantInvitationForm:
    """Tests for TenantInvitationForm."""

    def test_valid_form(self, tenant):
        """Test form with valid data."""
        form_data = {
            'email': 'newuser@example.com',
            'role': 'member'
        }
        form = TenantInvitationForm(data=form_data, tenant=tenant)
        assert form.is_valid()

    def test_form_rejects_existing_member(self, user, tenant, tenant_user):
        """Test form rejects email of existing tenant member."""
        form_data = {
            'email': user.email,
            'role': 'member'
        }
        form = TenantInvitationForm(data=form_data, tenant=tenant)
        assert not form.is_valid()
        assert 'email' in form.errors
        assert 'already a member' in str(form.errors['email']).lower()

    def test_form_rejects_pending_invitation(self, tenant, invitation):
        """Test form rejects email with pending invitation."""
        form_data = {
            'email': invitation.email,
            'role': 'member'
        }
        form = TenantInvitationForm(data=form_data, tenant=tenant)
        assert not form.is_valid()
        assert 'email' in form.errors
        assert 'pending invitation' in str(form.errors['email']).lower()

    def test_form_allows_non_existing_user(self, tenant):
        """Test form allows email for non-existing user."""
        form_data = {
            'email': 'newuser@example.com',
            'role': 'admin'
        }
        form = TenantInvitationForm(data=form_data, tenant=tenant)
        assert form.is_valid()

    def test_invalid_email(self, tenant):
        """Test form rejects invalid email."""
        form_data = {
            'email': 'not-an-email',
            'role': 'member'
        }
        form = TenantInvitationForm(data=form_data, tenant=tenant)
        assert not form.is_valid()
        assert 'email' in form.errors
