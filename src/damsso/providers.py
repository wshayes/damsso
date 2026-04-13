"""
SSO provider implementations for OIDC and SAML.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from authlib.jose import JsonWebKey, jwt as jose_jwt
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import SSOProvider
from .oidc_utils import oidc_http_timeout

User = get_user_model()
logger = logging.getLogger(__name__)

# Shared OAuth instance for all OIDC providers
# This ensures session state is maintained across requests
_oauth_registry = OAuth()


def _requests_get_json(url: str) -> dict[str, Any]:
    r = requests.get(url, timeout=oidc_http_timeout())
    r.raise_for_status()
    return r.json()


def _requests_post_form(url: str, data: dict[str, Any]) -> requests.Response:
    return requests.post(url, data=data, timeout=oidc_http_timeout())


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
        if sso_provider.protocol != "oidc":
            raise ValueError("SSO Provider must be OIDC protocol")

        self.provider = sso_provider
        self.oauth = _oauth_registry  # Use shared OAuth instance

        # Generate consistent client name for this tenant
        self.client_name = f"tenant_{sso_provider.tenant.pk}"

        # Configure OAuth client
        client_kwargs = {"scope": sso_provider.oidc_scopes or "openid email profile"}

        # Check if client is already registered, if so, unregister it first
        # This ensures we always use the latest configuration
        if hasattr(self.oauth, "_clients") and self.client_name in self.oauth._clients:
            del self.oauth._clients[self.client_name]

        # Use discovery if issuer is provided
        if sso_provider.oidc_issuer:
            self.oauth.register(
                name=self.client_name,
                client_id=sso_provider.oidc_client_id,
                client_secret=sso_provider.oidc_client_secret,
                server_metadata_url=f"{sso_provider.oidc_issuer}/.well-known/openid-configuration",
                client_kwargs=client_kwargs,
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
                client_kwargs=client_kwargs,
            )

        self.client = self.oauth.create_client(self.client_name)

    def _issuer_metadata(self) -> dict[str, Any] | None:
        """OpenID discovery document when oidc_issuer is configured."""
        if not self.provider.oidc_issuer:
            return None
        url = f"{self.provider.oidc_issuer}/.well-known/openid-configuration"
        return _requests_get_json(url)

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
        from urllib.parse import urlencode

        # Generate our own state to avoid authlib session issues
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state and nonce in Django session with a unique key
        session_key = f"_oauth_state_{self.client_name}"
        request.session[session_key] = {
            "state": state,
            "nonce": nonce,
            "redirect_uri": redirect_uri,
        }
        # Mark session as modified if it's a real Django session
        if hasattr(request.session, "modified"):
            request.session.modified = True

        # Build authorization URL manually
        params = {
            "response_type": "code",
            "client_id": self.provider.oidc_client_id,
            "redirect_uri": redirect_uri,
            "scope": self.provider.oidc_scopes or "openid email profile",
            "state": state,
            "nonce": nonce,
        }

        # Get authorization endpoint
        if self.provider.oidc_issuer:
            metadata = self._issuer_metadata()
            authorization_endpoint = metadata["authorization_endpoint"]
        else:
            authorization_endpoint = self.provider.oidc_authorization_endpoint

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
        # Validate state
        session_key = f"_oauth_state_{self.client_name}"
        session_data = request.session.get(session_key)

        if not session_data:
            raise ValueError("No OAuth state found in session")

        # Get state from callback
        callback_state = request.GET.get("state")
        if not callback_state:
            raise ValueError("No state parameter in callback")

        # Verify state matches
        if callback_state != session_data["state"]:
            raise ValueError(f"State mismatch: expected {session_data['state']}, got {callback_state}")

        # Get authorization code
        code = request.GET.get("code")
        if not code:
            error = request.GET.get("error", "unknown_error")
            error_description = request.GET.get("error_description", "No description provided")
            raise ValueError(f"OAuth error: {error} - {error_description}")

        nonce = session_data.get("nonce")

        # Get token endpoint
        if self.provider.oidc_issuer:
            metadata = self._issuer_metadata()
            token_endpoint = metadata["token_endpoint"]
        else:
            token_endpoint = self.provider.oidc_token_endpoint

        # Exchange code for token
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.provider.oidc_client_id,
            "client_secret": self.provider.oidc_client_secret,
        }

        token_response = _requests_post_form(token_endpoint, data=token_data)
        token_response.raise_for_status()
        token = token_response.json()

        # Preserve nonce for ID token validation in get_userinfo (session row is removed below)
        if nonce:
            token["_damsso_oidc_nonce"] = nonce

        # Clean up session
        if session_key in request.session:
            del request.session[session_key]
        if hasattr(request.session, "modified"):
            request.session.modified = True

        return token

    def _jwks_uri(self, metadata: dict[str, Any] | None) -> str | None:
        if metadata and metadata.get("jwks_uri"):
            return metadata["jwks_uri"]
        return self.provider.oidc_jwks_uri or None

    def _expected_issuer(self, metadata: dict[str, Any] | None) -> str | None:
        if metadata and metadata.get("issuer"):
            return metadata["issuer"]
        if self.provider.oidc_issuer:
            return str(self.provider.oidc_issuer).rstrip("/")
        return None

    def _decode_id_token_verified(
        self,
        id_token: str,
        nonce: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Verify and decode an OIDC ID token (RS/EC via JWKS, or HS256 with client_secret).
        """
        jwks_uri = self._jwks_uri(metadata)
        expected_iss = self._expected_issuer(metadata)
        client_id = self.provider.oidc_client_id

        if not expected_iss:
            raise ValueError(
                "Cannot verify ID token: configure oidc_issuer (discovery) "
                "or ensure issuer is present in provider metadata."
            )

        import base64
        import json

        # Inspect header for algorithm
        header_segment = id_token.split(".")[0]
        pad = 4 - len(header_segment) % 4
        if pad != 4:
            header_segment += "=" * pad

        header = json.loads(base64.urlsafe_b64decode(header_segment.encode("ascii")))
        alg = header.get("alg") or "RS256"

        if alg == "HS256":
            secret = self.provider.oidc_client_secret
            if not secret:
                raise ValueError("Cannot verify HS256 ID token without client_secret.")
            claims = jose_jwt.decode(
                id_token,
                secret,
                claims_options={
                    "iss": {"essential": True, "value": expected_iss},
                    "aud": {"essential": True, "value": client_id},
                },
            )
        else:
            if not jwks_uri:
                raise ValueError(
                    "Cannot verify ID token: no JWKS URI (configure issuer discovery "
                    "or set oidc_jwks_uri on the provider)."
                )
            jwks = _requests_get_json(jwks_uri)
            key_set = JsonWebKey.import_key_set(jwks)
            claims_options: dict[str, dict[str, Any]] = {
                "iss": {"essential": True, "value": expected_iss},
                "aud": {"essential": True, "value": client_id},
            }
            if nonce:
                claims_options["nonce"] = {"essential": True, "value": nonce}

            claims = jose_jwt.decode(id_token, key_set, claims_options=claims_options)

        try:
            claims.validate()
        except Exception as exc:
            logger.warning("ID token claims validation failed: %s", exc)
            raise ValueError("ID token validation failed") from exc

        # Normalise to plain dict for callers
        return dict(claims)

    def get_userinfo(self, token):
        """
        Get user information from OIDC provider.

        Prefers the userinfo endpoint when available. ID tokens are only accepted
        after cryptographic verification (JWKS / client secret for HS256).
        """
        metadata = self._issuer_metadata() if self.provider.oidc_issuer else None

        if self.provider.oidc_issuer:
            assert metadata is not None
            userinfo_endpoint = metadata.get("userinfo_endpoint")
        else:
            userinfo_endpoint = self.provider.oidc_userinfo_endpoint

        if userinfo_endpoint and "access_token" in token:
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            response = requests.get(userinfo_endpoint, headers=headers, timeout=oidc_http_timeout())
            response.raise_for_status()
            return response.json()

        id_token = token.get("id_token")
        if not id_token:
            raise ValueError(
                "OIDC provider returned no userinfo and no id_token; cannot determine user identity."
            )

        nonce = token.get("_damsso_oidc_nonce")
        userinfo = self._decode_id_token_verified(id_token, nonce, metadata)
        return userinfo

    def test_connection(self):
        """
        Test OIDC provider connection.

        Returns:
            dict: Test results with success status and details
        """
        try:
            # Try to fetch OpenID configuration
            if self.provider.oidc_issuer:
                config_url = f"{self.provider.oidc_issuer}/.well-known/openid-configuration"
                response = requests.get(config_url, timeout=10)
                response.raise_for_status()
                config = response.json()

                return {
                    "success": True,
                    "message": "OIDC provider configuration retrieved successfully",
                    "details": {
                        "issuer": config.get("issuer"),
                        "authorization_endpoint": config.get("authorization_endpoint"),
                        "token_endpoint": config.get("token_endpoint"),
                        "userinfo_endpoint": config.get("userinfo_endpoint"),
                        "scopes_supported": config.get("scopes_supported", []),
                    },
                }
            else:
                # Check if endpoints are reachable
                endpoints_ok = True
                details: dict[str, Any] = {}

                for endpoint_name, endpoint_url in [
                    ("authorization", self.provider.oidc_authorization_endpoint),
                    ("token", self.provider.oidc_token_endpoint),
                    ("userinfo", self.provider.oidc_userinfo_endpoint),
                ]:
                    if endpoint_url:
                        try:
                            response = requests.get(endpoint_url, timeout=5)
                            details[f"{endpoint_name}_endpoint"] = {
                                "url": endpoint_url,
                                "reachable": True,
                                "status": response.status_code,
                            }
                        except Exception as e:
                            details[f"{endpoint_name}_endpoint"] = {
                                "url": endpoint_url,
                                "reachable": False,
                                "error": str(e),
                            }
                            endpoints_ok = False

                if endpoints_ok:
                    return {
                        "success": True,
                        "message": "OIDC endpoints are reachable",
                        "details": details,
                    }
                else:
                    return {
                        "success": False,
                        "message": "Some OIDC endpoints are not reachable",
                        "details": details,
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect to OIDC provider: {str(e)}",
                "error": str(e),
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
        if sso_provider.protocol != "saml":
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
        from django.urls import reverse

        # Build absolute URLs for SAML endpoints
        acs_url = request.build_absolute_uri(reverse("damsso:saml_acs", args=[self.provider.tenant.pk]))
        metadata_url = request.build_absolute_uri(
            reverse("damsso:saml_metadata", args=[self.provider.tenant.pk])
        )

        saml_settings = {
            "strict": True,
            "debug": settings.DEBUG,
            "sp": {
                "entityId": metadata_url,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "attributeConsumingService": {
                    "serviceName": f"{self.provider.tenant.name} SSO",
                    "serviceDescription": f"SSO service for {self.provider.tenant.name}",
                    "requestedAttributes": [
                        {
                            "name": "email",
                            "isRequired": True,
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "friendlyName": "email",
                        },
                        {
                            "name": "firstName",
                            "isRequired": False,
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "friendlyName": "firstName",
                        },
                        {
                            "name": "lastName",
                            "isRequired": False,
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "friendlyName": "lastName",
                        },
                    ],
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": self.provider.saml_entity_id,
                "singleSignOnService": {
                    "url": self.provider.saml_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self._clean_certificate(self.provider.saml_x509_cert),
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": True,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "requestedAuthnContextComparison": "exact",
                "metadataValidUntil": None,
                "metadataCacheDuration": None,
            },
        }

        # Add SLO if configured
        if self.provider.saml_slo_url:
            saml_settings["idp"]["singleLogoutService"] = {
                "url": self.provider.saml_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
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
            return ""

        cert = cert.strip()
        cert = cert.replace("-----BEGIN CERTIFICATE-----", "")
        cert = cert.replace("-----END CERTIFICATE-----", "")
        cert = cert.replace("\n", "")
        cert = cert.replace("\r", "")
        cert = cert.replace(" ", "")
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
                return {"success": False, "message": "SAML Entity ID is required"}

            if not self.provider.saml_sso_url:
                return {"success": False, "message": "SAML SSO URL is required"}

            if not self.provider.saml_x509_cert:
                return {"success": False, "message": "SAML X.509 Certificate is required"}

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
                    cert_message = "Certificate format appears valid"
                else:
                    cert_valid = False
                    cert_message = "Certificate is empty"
            except Exception as e:
                cert_valid = False
                cert_message = f"Certificate validation failed: {str(e)}"

            details = {
                "entity_id": self.provider.saml_entity_id,
                "sso_url": {
                    "url": self.provider.saml_sso_url,
                    "reachable": sso_url_reachable,
                    "status": sso_url_status if sso_url_reachable else "N/A",
                    "error": sso_url_error if not sso_url_reachable else None,
                },
                "certificate": {"valid": cert_valid, "message": cert_message},
            }

            if sso_url_reachable and cert_valid:
                return {"success": True, "message": "SAML provider configuration is valid", "details": details}
            else:
                return {
                    "success": False,
                    "message": "SAML provider configuration has issues",
                    "details": details,
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to validate SAML provider: {str(e)}",
                "error": str(e),
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
    if sso_provider.protocol == "oidc":
        return OIDCProviderClient(sso_provider)
    elif sso_provider.protocol == "saml":
        return SAMLProviderClient(sso_provider)
    else:
        raise ValueError(f"Unsupported protocol: {sso_provider.protocol}")
