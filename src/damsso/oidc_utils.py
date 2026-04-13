"""
OIDC HTTP timeout helper for damsso (Django settings).
"""

from __future__ import annotations

from django.conf import settings


def oidc_http_timeout() -> float:
    """Seconds for outbound OIDC HTTP calls (metadata, JWKS, token, userinfo)."""
    return float(getattr(settings, "DAMSSO_OIDC_HTTP_TIMEOUT", 15))
