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

# Shared OAuth instance for all OIDC providers
# This ensures session state is maintained across requests
_oauth_registry = OAuth()


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
        self.oauth = _oauth_registry  # Use shared OAuth instance

        # Generate consistent client name for this tenant
        self.client_name = f'tenant_{sso_provider.tenant.pk}'

        # Configure OAuth client
        client_kwargs = {
            'scope': sso_provider.oidc_scopes or 'openid email profile'
        }

        # Check if client is already registered, if so, unregister it first
        # This ensures we always use the latest configuration
        if hasattr(self.oauth, '_clients') and self.client_name in self.oauth._clients:
            del self.oauth._clients[self.client_name]

        # Use discovery if issuer is provided
        if sso_provider.oidc_issuer:
            self.oauth.register(
                name=self.client_name,
                client_id=sso_provider.oidc_client_id,
                client_secret=sso_provider.oidc_client_secret,
                server_metadata_url=f'{sso_provider.oidc_issuer}/.well-known/openid-configuration',
                client_kwargs=client_kwargs
            )
        else:
            # Manual configuration
            self.oauth.register(
                name=self.client_name,
                client_id=sso_provider.oidc_client_id,
                client_secret=sso_provider.oidc_client_secret,
                authorize_url=sso_provider.oidc_authorization_endpoint,
                access_token_url=sso_provider.oidc_token_endpoint,
                userinfo_endpoint=sso_provider.oidc_userinfo_endpoint,
                jwks_uri=sso_provider.oidc_jwks_uri,
                client_kwargs=client_kwargs
            )

        self.client = self.oauth.create_client(self.client_name)

    def get_authorization_url(self, request, redirect_uri):
        """
        Get the authorization URL for starting OIDC flow.

        Args:
            request: Django request object
            redirect_uri: Callback URL after authentication

        Returns:
            tuple: (authorization_url, state)
        """
        import secrets

        # Generate our own state to avoid authlib session issues
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state and nonce in Django session with a unique key
        session_key = f"_oauth_state_{self.client_name}"
        request.session[session_key] = {
            'state': state,
            'nonce': nonce,
            'redirect_uri': redirect_uri
        }
        # Mark session as modified if it's a real Django session
        if hasattr(request.session, 'modified'):
            request.session.modified = True

        # Build authorization URL manually
        params = {
            'response_type': 'code',
            'client_id': self.provider.oidc_client_id,
            'redirect_uri': redirect_uri,
            'scope': self.provider.oidc_scopes or 'openid email profile',
            'state': state,
            'nonce': nonce,
        }

        # Get authorization endpoint
        if self.provider.oidc_issuer:
            # Fetch from well-known endpoint
            import requests
            well_known_url = f'{self.provider.oidc_issuer}/.well-known/openid-configuration'
            response = requests.get(well_known_url)
            metadata = response.json()
            authorization_endpoint = metadata['authorization_endpoint']
        else:
            authorization_endpoint = self.provider.oidc_authorization_endpoint

        # Build URL
        from urllib.parse import urlencode
        url = f"{authorization_endpoint}?{urlencode(params)}"

        return url, state

    def fetch_token(self, request, redirect_uri):
        """
        Exchange authorization code for access token.

        Args:
            request: Django request object with authorization code
            redirect_uri: Callback URL used in authorization

        Returns:
            dict: Token response
        """
        import requests
        from django.http import QueryDict

        # Validate state
        session_key = f"_oauth_state_{self.client_name}"
        session_data = request.session.get(session_key)

        if not session_data:
            raise ValueError("No OAuth state found in session")

        # Get state from callback
        callback_state = request.GET.get('state')
        if not callback_state:
            raise ValueError("No state parameter in callback")

        # Verify state matches
        if callback_state != session_data['state']:
            raise ValueError(f"State mismatch: expected {session_data['state']}, got {callback_state}")

        # Get authorization code
        code = request.GET.get('code')
        if not code:
            error = request.GET.get('error', 'unknown_error')
            error_description = request.GET.get('error_description', 'No description provided')
            raise ValueError(f"OAuth error: {error} - {error_description}")

        # Get token endpoint
        if self.provider.oidc_issuer:
            well_known_url = f'{self.provider.oidc_issuer}/.well-known/openid-configuration'
            response = requests.get(well_known_url)
            metadata = response.json()
            token_endpoint = metadata['token_endpoint']
        else:
            token_endpoint = self.provider.oidc_token_endpoint

        # Exchange code for token
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.provider.oidc_client_id,
            'client_secret': self.provider.oidc_client_secret,
        }

        token_response = requests.post(token_endpoint, data=token_data)
        token_response.raise_for_status()
        token = token_response.json()

        # Clean up session
        if session_key in request.session:
            del request.session[session_key]
        if hasattr(request.session, 'modified'):
            request.session.modified = True

        return token

    def get_userinfo(self, token):
        """
        Get user information from OIDC provider.

        Args:
            token: Token dict from provider containing access_token and id_token

        Returns:
            dict: User information
        """
        import requests

        # Get userinfo endpoint
        if self.provider.oidc_issuer:
            well_known_url = f'{self.provider.oidc_issuer}/.well-known/openid-configuration'
            response = requests.get(well_known_url)
            metadata = response.json()
            userinfo_endpoint = metadata.get('userinfo_endpoint')
        else:
            userinfo_endpoint = self.provider.oidc_userinfo_endpoint

        # Fetch user info from userinfo endpoint
        if userinfo_endpoint and 'access_token' in token:
            headers = {
                'Authorization': f"Bearer {token['access_token']}"
            }
            response = requests.get(userinfo_endpoint, headers=headers)
            response.raise_for_status()
            return response.json()

        # Fallback: Try to parse user info from ID token
        id_token = token.get('id_token')
        if id_token:
            # Decode without verification for now (verification would require fetching JWKS)
            import base64
            import json
            # Split the JWT and decode the payload
            parts = id_token.split('.')
            if len(parts) == 3:
                # Add padding if needed
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                decoded = base64.urlsafe_b64decode(payload)
                return json.loads(decoded)

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
            reverse('damsso:saml_acs', args=[self.provider.tenant.pk])
        )
        metadata_url = request.build_absolute_uri(
            reverse('damsso:saml_metadata', args=[self.provider.tenant.pk])
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
