"""
Tests for SSO providers in django-allauth-multitenant-sso.
"""
import pytest
import responses
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django_allauth_multitenant_sso.providers import (
    OIDCProviderClient,
    SAMLProviderClient,
    get_provider_client
)
from django_allauth_multitenant_sso.models import SSOProvider


class TestOIDCProviderClient:
    """Tests for OIDCProviderClient."""

    def test_init_with_oidc_provider(self, oidc_provider):
        """Test initializing OIDC client."""
        client = OIDCProviderClient(oidc_provider)
        assert client.provider == oidc_provider

    def test_init_with_wrong_protocol(self, saml_provider):
        """Test initializing OIDC client with SAML provider fails."""
        with pytest.raises(ValueError) as exc_info:
            OIDCProviderClient(saml_provider)
        assert 'must be OIDC protocol' in str(exc_info.value)

    @responses.activate
    def test_test_connection_with_issuer_success(self, oidc_provider):
        """Test connection test with issuer discovery."""
        # Mock OpenID configuration endpoint
        responses.add(
            responses.GET,
            'https://accounts.google.com/.well-known/openid-configuration',
            json={
                'issuer': 'https://accounts.google.com',
                'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_endpoint': 'https://accounts.google.com/oauth2/v4/token',
                'userinfo_endpoint': 'https://openidconnect.googleapis.com/v1/userinfo',
                'scopes_supported': ['openid', 'email', 'profile']
            },
            status=200
        )

        client = OIDCProviderClient(oidc_provider)
        result = client.test_connection()

        assert result['success'] is True
        assert 'configuration retrieved' in result['message'].lower()
        assert 'issuer' in result['details']

    @responses.activate
    def test_test_connection_with_issuer_failure(self, oidc_provider):
        """Test connection test failure."""
        # Mock failed endpoint
        responses.add(
            responses.GET,
            'https://accounts.google.com/.well-known/openid-configuration',
            json={'error': 'not found'},
            status=404
        )

        client = OIDCProviderClient(oidc_provider)
        result = client.test_connection()

        assert result['success'] is False
        assert 'error' in result or 'Failed' in result['message']

    def test_test_connection_without_issuer(self, tenant):
        """Test connection test with manual endpoints."""
        provider = SSOProvider.objects.create(
            tenant=tenant,
            name='Manual OIDC',
            protocol='oidc',
            oidc_client_id='client-id',
            oidc_client_secret='secret',
            oidc_authorization_endpoint='https://provider.com/auth',
            oidc_token_endpoint='https://provider.com/token',
            oidc_userinfo_endpoint='https://provider.com/userinfo'
        )

        client = OIDCProviderClient(provider)
        # This will try to reach the endpoints, but they're not mocked
        # So it should fail gracefully
        result = client.test_connection()
        assert 'success' in result
        assert 'message' in result


class TestSAMLProviderClient:
    """Tests for SAMLProviderClient."""

    def test_init_with_saml_provider(self, saml_provider):
        """Test initializing SAML client."""
        client = SAMLProviderClient(saml_provider)
        assert client.provider == saml_provider

    def test_init_with_wrong_protocol(self, oidc_provider):
        """Test initializing SAML client with OIDC provider fails."""
        with pytest.raises(ValueError) as exc_info:
            SAMLProviderClient(oidc_provider)
        assert 'must be SAML protocol' in str(exc_info.value)

    def test_clean_certificate(self, saml_provider):
        """Test certificate cleaning."""
        client = SAMLProviderClient(saml_provider)

        # Test with full PEM format
        cert_with_headers = """-----BEGIN CERTIFICATE-----
MIIDEzCCAfugAwIBAgIJAKoSdj
-----END CERTIFICATE-----"""

        cleaned = client._clean_certificate(cert_with_headers)
        assert '-----BEGIN CERTIFICATE-----' not in cleaned
        assert '-----END CERTIFICATE-----' not in cleaned
        assert '\n' not in cleaned
        assert 'MIIDEzCCAfugAwIBAgIJAKoSdj' in cleaned

    def test_clean_certificate_empty(self, saml_provider):
        """Test cleaning empty certificate."""
        client = SAMLProviderClient(saml_provider)
        cleaned = client._clean_certificate('')
        assert cleaned == ''

    def test_get_saml_settings(self, saml_provider):
        """Test getting SAML settings."""
        client = SAMLProviderClient(saml_provider)
        factory = RequestFactory()
        request = factory.get('/test/')

        settings = client.get_saml_settings(request)

        assert settings['strict'] is True
        assert 'sp' in settings
        assert 'idp' in settings
        assert settings['idp']['entityId'] == saml_provider.saml_entity_id
        assert settings['idp']['singleSignOnService']['url'] == saml_provider.saml_sso_url

    def test_get_saml_settings_with_slo(self, tenant):
        """Test SAML settings with SLO URL."""
        provider = SSOProvider.objects.create(
            tenant=tenant,
            name='SAML with SLO',
            protocol='saml',
            saml_entity_id='https://idp.example.com',
            saml_sso_url='https://idp.example.com/sso',
            saml_slo_url='https://idp.example.com/slo',
            saml_x509_cert='MIIDEzCCAfugAwIBAgIJAKoSdj'
        )

        client = SAMLProviderClient(provider)
        factory = RequestFactory()
        request = factory.get('/test/')

        settings = client.get_saml_settings(request)
        assert 'singleLogoutService' in settings['idp']
        assert settings['idp']['singleLogoutService']['url'] == provider.saml_slo_url

    @responses.activate
    def test_test_connection_success(self, saml_provider):
        """Test successful SAML connection test."""
        # Mock SSO URL endpoint
        responses.add(
            responses.GET,
            saml_provider.saml_sso_url,
            body='<html>IdP Login</html>',
            status=200
        )

        client = SAMLProviderClient(saml_provider)
        result = client.test_connection()

        assert result['success'] is True
        assert 'configuration is valid' in result['message'].lower()
        assert result['details']['sso_url']['reachable'] is True
        assert result['details']['certificate']['valid'] is True

    @responses.activate
    def test_test_connection_unreachable_url(self, saml_provider):
        """Test SAML connection test with unreachable URL."""
        # Don't mock the endpoint, so it will fail
        client = SAMLProviderClient(saml_provider)
        result = client.test_connection()

        # Should still return a result but with success=False or partial success
        assert 'success' in result
        assert 'details' in result

    def test_test_connection_missing_entity_id(self, tenant):
        """Test connection test with missing entity ID."""
        provider = SSOProvider.objects.create(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_sso_url='https://idp.example.com/sso',
            saml_x509_cert='cert'
        )

        client = SAMLProviderClient(provider)
        result = client.test_connection()

        assert result['success'] is False
        assert 'Entity ID is required' in result['message']

    def test_test_connection_missing_sso_url(self, tenant):
        """Test connection test with missing SSO URL."""
        provider = SSOProvider.objects.create(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_entity_id='https://idp.example.com',
            saml_x509_cert='cert'
        )

        client = SAMLProviderClient(provider)
        result = client.test_connection()

        assert result['success'] is False
        assert 'SSO URL is required' in result['message']

    def test_test_connection_missing_cert(self, tenant):
        """Test connection test with missing certificate."""
        provider = SSOProvider.objects.create(
            tenant=tenant,
            name='Invalid SAML',
            protocol='saml',
            saml_entity_id='https://idp.example.com',
            saml_sso_url='https://idp.example.com/sso'
        )

        client = SAMLProviderClient(provider)
        result = client.test_connection()

        assert result['success'] is False
        assert 'Certificate is required' in result['message']


class TestGetProviderClient:
    """Tests for get_provider_client factory function."""

    def test_returns_oidc_client(self, oidc_provider):
        """Test factory returns OIDC client for OIDC provider."""
        client = get_provider_client(oidc_provider)
        assert isinstance(client, OIDCProviderClient)

    def test_returns_saml_client(self, saml_provider):
        """Test factory returns SAML client for SAML provider."""
        client = get_provider_client(saml_provider)
        assert isinstance(client, SAMLProviderClient)

    def test_raises_for_unknown_protocol(self, tenant):
        """Test factory raises error for unknown protocol."""
        provider = SSOProvider(
            tenant=tenant,
            name='Unknown',
            protocol='unknown'
        )

        with pytest.raises(ValueError) as exc_info:
            get_provider_client(provider)
        assert 'Unsupported protocol' in str(exc_info.value)
