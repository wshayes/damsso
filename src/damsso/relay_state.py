"""
SAML RelayState validation (stdlib only — safe to import without Django).
"""

from __future__ import annotations

from urllib.parse import urlparse


def safe_saml_relay_path(relay_state: str | None) -> str | None:
    """
    Return a safe in-app path for SAML RelayState, or None if unsafe.

    Rejects absolute URLs, scheme-relative URLs, and backslash tricks to
    avoid open redirects after ACS.
    """
    if not relay_state:
        return None
    rs = relay_state.strip()
    if not rs.startswith("/") or rs.startswith("//"):
        return None
    if "\\" in rs:
        return None
    parsed = urlparse(rs)
    if parsed.scheme or parsed.netloc:
        return None
    return rs
