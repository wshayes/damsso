"""
SSO provider implementations for OIDC and SAML.
"""
from authlib.integrations.django_client import OAuth
from authlib.jose import jwt
from authlib.oidc.core import CodeIDToken
import requests
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SSOProvider, Tenant


User = get_user_model()


class OIDCProviderClient:
    """
    Client for handling OIDC authentication flow.
    """

    def __init__(self, sso_provider: SSOProvider):
        """
        Initialize OIDC client with provider configuration.

        Args:
            sso_provider: SSOProvider instance with OIDC configuration
        """
        if sso_provider.protocol != 'oidc':
            raise ValueError("SSO Provider must be OIDC protocol")

        self.provider = sso_provider
        self.oauth = OAuth()

        # Configure OAuth client
        client_kwargs = {
            'scope': sso_provider.oidc_scopes or 'openid email profile'
        }

        # Use discovery if issuer is provided
        if sso_provider.oidc_issuer:
            self.oauth.register(
                name=f'tenant_{sso_provider.tenant.id}',
                client_id=sso_provider.oidc_client_id,
                client_secret=sso_provider.oidc_client_secret,
                server_metadata_url=f'{sso_provider.oidc_issuer}/.well-known/openid-configuration',
                client_kwargs=client_kwargs
            )
        else:
            # Manual configuration
            self.oauth.register(
                name=f'tenant_{sso_provider.tenant.id}',
                client_id=sso_provider.oidc_client_id,
                client_secret=sso_provider.oidc_client_secret,
                authorize_url=sso_provider.oidc_authorization_endpoint,
                access_token_url=sso_provider.oidc_token_endpoint,
                userinfo_endpoint=sso_provider.oidc_userinfo_endpoint,
                jwks_uri=sso_provider.oidc_jwks_uri,
                client_kwargs=client_kwargs
            )

        self.client = self.oauth.create_client(f'tenant_{sso_provider.tenant.id}')

    def get_authorization_url(self, request, redirect_uri):
        """
        Get the authorization URL for starting OIDC flow.

        Args:
            request: Django request object
            redirect_uri: Callback URL after authentication

        Returns:
            tuple: (authorization_url, state)
        """
        return self.client.create_authorization_url(
            redirect_uri=redirect_uri,
            state=request.session.get('oidc_state')
        )

    def fetch_token(self, request, redirect_uri):
        """
        Exchange authorization code for access token.

        Args:
            request: Django request object with authorization code
            redirect_uri: Callback URL used in authorization

        Returns:
            dict: Token response
        """
        return self.client.authorize_access_token(request, redirect_uri=redirect_uri)

    def get_userinfo(self, token):
        """
        Get user information from OIDC provider.

        Args:
            token: Access token from provider

        Returns:
            dict: User information
        """
        if self.provider.oidc_userinfo_endpoint:
            response = self.client.get(
                self.provider.oidc_userinfo_endpoint,
                token=token
            )
            return response.json()
        else:
            # Try to parse user info from ID token
            id_token = token.get('id_token')
            if id_token:
                claims = jwt.decode(id_token, self.provider.oidc_client_secret)
                return claims
        return {}

    def test_connection(self):
        """
        Test OIDC provider connection.

        Returns:
            dict: Test results with success status and details
        """
        try:
            # Try to fetch OpenID configuration
            if self.provider.oidc_issuer:
                config_url = f'{self.provider.oidc_issuer}/.well-known/openid-configuration'
                response = requests.get(config_url, timeout=10)
                response.raise_for_status()
                config = response.json()

                return {
                    'success': True,
                    'message': 'OIDC provider configuration retrieved successfully',
                    'details': {
                        'issuer': config.get('issuer'),
                        'authorization_endpoint': config.get('authorization_endpoint'),
                        'token_endpoint': config.get('token_endpoint'),
                        'userinfo_endpoint': config.get('userinfo_endpoint'),
                        'scopes_supported': config.get('scopes_supported', [])
                    }
                }
            else:
                # Check if endpoints are reachable
                endpoints_ok = True
                details = {}

                for endpoint_name, endpoint_url in [
                    ('authorization', self.provider.oidc_authorization_endpoint),
                    ('token', self.provider.oidc_token_endpoint),
                    ('userinfo', self.provider.oidc_userinfo_endpoint)
                ]:
                    if endpoint_url:
                        try:
                            response = requests.get(endpoint_url, timeout=5)
                            details[f'{endpoint_name}_endpoint'] = {
                                'url': endpoint_url,
                                'reachable': True,
                                'status': response.status_code
                            }
                        except Exception as e:
                            details[f'{endpoint_name}_endpoint'] = {
                                'url': endpoint_url,
                                'reachable': False,
                                'error': str(e)
                            }
                            endpoints_ok = False

                if endpoints_ok:
                    return {
                        'success': True,
                        'message': 'OIDC endpoints are reachable',
                        'details': details
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Some OIDC endpoints are not reachable',
                        'details': details
                    }

        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to connect to OIDC provider: {str(e)}',
                'error': str(e)
            }


class SAMLProviderClient:
    """
    Client for handling SAML authentication flow.
    """

    def __init__(self, sso_provider: SSOProvider):
        """
        Initialize SAML client with provider configuration.

        Args:
            sso_provider: SSOProvider instance with SAML configuration
        """
        if sso_provider.protocol != 'saml':
            raise ValueError("SSO Provider must be SAML protocol")

        self.provider = sso_provider

    def get_saml_settings(self, request):
        """
        Get SAML settings dictionary for python3-saml.

        Args:
            request: Django request object

        Returns:
            dict: SAML settings
        """
        # Build absolute URLs for SAML endpoints
        acs_url = request.build_absolute_uri(
            reverse('allauth_multitenant_sso:saml_acs', args=[self.provider.tenant.id])
        )
        metadata_url = request.build_absolute_uri(
            reverse('allauth_multitenant_sso:saml_metadata', args=[self.provider.tenant.id])
        )

        # Parse attribute mapping
        attribute_mapping = self.provider.saml_attribute_mapping or {}

        saml_settings = {
            'strict': True,
            'debug': settings.DEBUG,
            'sp': {
                'entityId': metadata_url,
                'assertionConsumerService': {
                    'url': acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'attributeConsumingService': {
                    'serviceName': f'{self.provider.tenant.name} SSO',
                    'serviceDescription': f'SSO service for {self.provider.tenant.name}',
                    'requestedAttributes': [
                        {
                            'name': 'email',
                            'isRequired': True,
                            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:basic',
                            'friendlyName': 'email'
                        },
                        {
                            'name': 'firstName',
                            'isRequired': False,
                            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:basic',
                            'friendlyName': 'firstName'
                        },
                        {
                            'name': 'lastName',
                            'isRequired': False,
                            'nameFormat': 'urn:oasis:names:tc:SAML:2.0:attrname-format:basic',
                            'friendlyName': 'lastName'
                        }
                    ]
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
            },
            'idp': {
                'entityId': self.provider.saml_entity_id,
                'singleSignOnService': {
                    'url': self.provider.saml_sso_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': self._clean_certificate(self.provider.saml_x509_cert)
            },
            'security': {
                'nameIdEncrypted': False,
                'authnRequestsSigned': False,
                'logoutRequestSigned': False,
                'logoutResponseSigned': False,
                'signMetadata': False,
                'wantMessagesSigned': False,
                'wantAssertionsSigned': True,
                'wantAssertionsEncrypted': False,
                'wantNameIdEncrypted': False,
                'requestedAuthnContext': True,
                'requestedAuthnContextComparison': 'exact',
                'metadataValidUntil': None,
                'metadataCacheDuration': None,
            }
        }

        # Add SLO if configured
        if self.provider.saml_slo_url:
            saml_settings['idp']['singleLogoutService'] = {
                'url': self.provider.saml_slo_url,
                'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
            }

        return saml_settings

    def _clean_certificate(self, cert):
        """
        Clean certificate string by removing headers and whitespace.

        Args:
            cert: Certificate string

        Returns:
            str: Cleaned certificate
        """
        if not cert:
            return ''

        cert = cert.strip()
        cert = cert.replace('-----BEGIN CERTIFICATE-----', '')
        cert = cert.replace('-----END CERTIFICATE-----', '')
        cert = cert.replace('\n', '')
        cert = cert.replace('\r', '')
        cert = cert.replace(' ', '')
        return cert

    def test_connection(self):
        """
        Test SAML provider configuration.

        Returns:
            dict: Test results with success status and details
        """
        try:
            # Basic validation
            if not self.provider.saml_entity_id:
                return {
                    'success': False,
                    'message': 'SAML Entity ID is required'
                }

            if not self.provider.saml_sso_url:
                return {
                    'success': False,
                    'message': 'SAML SSO URL is required'
                }

            if not self.provider.saml_x509_cert:
                return {
                    'success': False,
                    'message': 'SAML X.509 Certificate is required'
                }

            # Test if SSO URL is reachable
            try:
                response = requests.get(self.provider.saml_sso_url, timeout=10)
                sso_url_reachable = True
                sso_url_status = response.status_code
            except Exception as e:
                sso_url_reachable = False
                sso_url_error = str(e)

            # Validate certificate format
            try:
                cleaned_cert = self._clean_certificate(self.provider.saml_x509_cert)
                if len(cleaned_cert) > 0:
                    cert_valid = True
                    cert_message = 'Certificate format appears valid'
                else:
                    cert_valid = False
                    cert_message = 'Certificate is empty'
            except Exception as e:
                cert_valid = False
                cert_message = f'Certificate validation failed: {str(e)}'

            details = {
                'entity_id': self.provider.saml_entity_id,
                'sso_url': {
                    'url': self.provider.saml_sso_url,
                    'reachable': sso_url_reachable,
                    'status': sso_url_status if sso_url_reachable else 'N/A',
                    'error': sso_url_error if not sso_url_reachable else None
                },
                'certificate': {
                    'valid': cert_valid,
                    'message': cert_message
                }
            }

            if sso_url_reachable and cert_valid:
                return {
                    'success': True,
                    'message': 'SAML provider configuration is valid',
                    'details': details
                }
            else:
                return {
                    'success': False,
                    'message': 'SAML provider configuration has issues',
                    'details': details
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to validate SAML provider: {str(e)}',
                'error': str(e)
            }


def get_provider_client(sso_provider: SSOProvider):
    """
    Factory function to get the appropriate provider client.

    Args:
        sso_provider: SSOProvider instance

    Returns:
        OIDCProviderClient or SAMLProviderClient instance

    Raises:
        ValueError: If protocol is not supported
    """
    if sso_provider.protocol == 'oidc':
        return OIDCProviderClient(sso_provider)
    elif sso_provider.protocol == 'saml':
        return SAMLProviderClient(sso_provider)
    else:
        raise ValueError(f"Unsupported protocol: {sso_provider.protocol}")
