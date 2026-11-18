"""URL validation and SSRF protection utilities.

The /link-analysis endpoint accepts arbitrary user-supplied URLs, so we must
prevent Server-Side Request Forgery: requests to localhost, private/internal
network ranges, cloud metadata endpoints, and non-HTTP schemes are rejected.
"""
import ipaddress
import socket
from urllib.parse import urlparse


class InvalidURLError(ValueError):
    """Raised when the submitted URL is malformed or blocked."""


class PrivateAddressError(InvalidURLError):
    """Raised when the URL resolves to a private / internal network address."""


ALLOWED_SCHEMES = {"http", "https"}


def _is_public_ip(ip: str) -> bool:
    """Return True only for globally-routable public addresses."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # is_global excludes loopback, RFC1918, link-local, multicast, reserved.
    return addr.is_global and not addr.is_multicast


def validate_url(url: str) -> str:
    """Validate a user-supplied website URL. Returns the cleaned URL.

    Raises InvalidURLError / PrivateAddressError on bad or unsafe input.
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL is required.")

    url = url.strip()
    if len(url) > 2048:
        raise InvalidURLError("URL is too long.")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidURLError("URL must start with http:// or https://")
    if not parsed.hostname:
        raise InvalidURLError("URL must contain a valid hostname.")
    if parsed.port is not None and (parsed.port < 1 or parsed.port > 65535):
        raise InvalidURLError("URL contains an invalid port.")
    # Block credentials embedded in URL (user:pass@host) — common SSRF trick.
    if parsed.username or parsed.password:
        raise InvalidURLError("URLs containing credentials are not allowed.")

    hostname = parsed.hostname.lower()

    # Localhost / .local names never resolve to a public host.
    if hostname in ("localhost",) or hostname.endswith(".localhost") or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise PrivateAddressError(f"Access to '{hostname}' is not allowed.")

    # If the hostname is itself a literal IP, check it directly.
    try:
        ipaddress.ip_address(hostname)
        if not _is_public_ip(hostname):
            raise PrivateAddressError(f"Access to IP address '{hostname}' is not allowed.")
        return url
    except ValueError:
        pass  # hostname is a DNS name, resolve it below

    # Resolve DNS and verify every returned address is public (DNS-rebinding safe).
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise InvalidURLError(f"Could not resolve hostname '{hostname}'.") from exc

    addresses = {info[4][0] for info in infos}
    for addr in addresses:
        if not _is_public_ip(addr):
            raise PrivateAddressError(
                f"'{hostname}' resolves to a private/internal address ({addr})."
            )
    return url
