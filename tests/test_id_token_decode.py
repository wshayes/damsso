"""ID token verification (`OIDCProviderClient._decode_id_token_verified`).

These guard the joserfc-based verification: a valid token decodes, and a token
with a bad signature, wrong audience, wrong nonce, or past expiry is rejected.
"""

import time

import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, OctKey, RSAKey

from damsso.providers import OIDCProviderClient

ISS = "https://accounts.google.com"
AUD = "test-client-id"


def _base_claims(**overrides):
    now = int(time.time())
    claims = {"iss": ISS, "aud": AUD, "sub": "user-1", "exp": now + 3600, "iat": now}
    claims.update(overrides)
    return claims


@pytest.mark.django_db
class TestHS256:
    def test_valid_token_decodes(self, oidc_provider):
        client = OIDCProviderClient(oidc_provider)
        token = jwt.encode({"alg": "HS256"}, _base_claims(), OctKey.import_key("test-client-secret"))
        claims = client._decode_id_token_verified(token, nonce=None, metadata=None)
        assert claims["sub"] == "user-1"

    def test_wrong_secret_is_rejected(self, oidc_provider):
        client = OIDCProviderClient(oidc_provider)
        token = jwt.encode({"alg": "HS256"}, _base_claims(), OctKey.import_key("attacker-secret"))
        with pytest.raises(Exception):  # bad signature never yields claims
            client._decode_id_token_verified(token, nonce=None, metadata=None)

    def test_wrong_audience_is_rejected(self, oidc_provider):
        client = OIDCProviderClient(oidc_provider)
        token = jwt.encode(
            {"alg": "HS256"}, _base_claims(aud="someone-else"), OctKey.import_key("test-client-secret")
        )
        with pytest.raises(ValueError):
            client._decode_id_token_verified(token, nonce=None, metadata=None)

    def test_expired_token_is_rejected(self, oidc_provider):
        client = OIDCProviderClient(oidc_provider)
        token = jwt.encode(
            {"alg": "HS256"}, _base_claims(exp=int(time.time()) - 10), OctKey.import_key("test-client-secret")
        )
        with pytest.raises(ValueError):
            client._decode_id_token_verified(token, nonce=None, metadata=None)


@pytest.mark.django_db
class TestRS256ViaJWKS:
    def _setup(self, oidc_provider, monkeypatch):
        oidc_provider.oidc_jwks_uri = "https://idp.example.com/jwks"
        oidc_provider.save()
        key = RSAKey.generate_key(2048, auto_kid=True)
        jwks = KeySet([key]).as_dict(private=False)
        monkeypatch.setattr("damsso.providers._requests_get_json", lambda url: jwks)
        return key

    def _sign(self, key, **claim_overrides):
        return jwt.encode({"alg": "RS256", "kid": key.kid}, _base_claims(**claim_overrides), key)

    def test_valid_token_decodes(self, oidc_provider, monkeypatch):
        key = self._setup(oidc_provider, monkeypatch)
        client = OIDCProviderClient(oidc_provider)
        token = self._sign(key, nonce="n1")
        claims = client._decode_id_token_verified(token, nonce="n1", metadata=None)
        assert claims["sub"] == "user-1"

    def test_wrong_nonce_is_rejected(self, oidc_provider, monkeypatch):
        key = self._setup(oidc_provider, monkeypatch)
        client = OIDCProviderClient(oidc_provider)
        token = self._sign(key, nonce="n1")
        with pytest.raises(ValueError):
            client._decode_id_token_verified(token, nonce="WRONG", metadata=None)

    def test_token_signed_by_a_different_key_is_rejected(self, oidc_provider, monkeypatch):
        self._setup(oidc_provider, monkeypatch)  # JWKS advertises the legitimate key
        attacker = RSAKey.generate_key(2048, auto_kid=True)
        client = OIDCProviderClient(oidc_provider)
        forged = jwt.encode({"alg": "RS256", "kid": attacker.kid}, _base_claims(), attacker)
        with pytest.raises(Exception):
            client._decode_id_token_verified(forged, nonce=None, metadata=None)
