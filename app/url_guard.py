# ==============================================================================
# app/url_guard.py - refuse outbound requests that would reach this machine or LAN
#
# Why: the fetch_json tool lets the language model name any http(s) URL. Without a
# check it can be steered (by a prompt in a web page, a file, or a redirect) into
# requesting http://127.0.0.1:3210/... (this app's own control API), cloud metadata
# at 169.254.169.254, a router admin page or any LAN device: server-side request
# forgery (SSRF). This module answers one question, "does this URL point at a
# publicly routable address?", using only the standard library so it imports (and
# is unit-tested) without httpx.
#
# How it fits: app/facts.py retrieve_json() calls ensure_public_url() for the first
# URL and again for EVERY redirect target (a public host can 302 to 127.0.0.1).
#
# Design: resolve the host name ourselves (getaddrinfo) and require EVERY returned
# address to be globally routable; one private answer is enough to refuse, because a
# resolver can return a mixed set. IPv4-mapped IPv6 (::ffff:127.0.0.1) is unwrapped
# first so it cannot smuggle a loopback address past the IPv6 checks.
# Known limit: DNS rebinding (a name that answers public to this check and private to
# the later connection) is not closed here, because the HTTP client resolves again;
# pinning the connection to the validated address would be the next hardening step.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Public-address check for outbound URLs (SSRF guard)."""
import ipaddress
import socket
from urllib.parse import urlsplit


class BlockedURL(ValueError):
    """Raised when a URL is malformed or targets a non-public address."""


def address_is_public(address):
    """Return True when an IP address string is globally routable.

    Args:
        address: IPv4/IPv6 text as returned by getaddrinfo (may carry a %zone suffix).
    Returns:
        False for loopback, private (RFC 1918 / ULA), link-local (incl. cloud metadata
        169.254.169.254), carrier-grade NAT, multicast, reserved and unspecified
        addresses; True otherwise.
    """
    # A zone id ("fe80::1%en0") is not accepted by ipaddress and is irrelevant to the verdict.
    ip = ipaddress.ip_address(address.split('%', 1)[0])
    # ::ffff:a.b.c.d is an IPv4 address in IPv6 clothing; judge the embedded IPv4 instead.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(ip.is_global) and not (ip.is_multicast or ip.is_loopback or ip.is_link_local
                                       or ip.is_private or ip.is_reserved or ip.is_unspecified)


def _system_resolver(host, port):
    """Resolve a host name to the list of address strings the OS would connect to."""
    return [info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def ensure_public_url(url, resolver=None):
    """Validate that an http(s) URL points only at public addresses.

    Args:
        url: absolute URL string.
        resolver: optional callable (host, port) -> iterable of address strings; tests
            inject one so no real DNS is needed. Defaults to the system resolver.
    Raises:
        BlockedURL: bad scheme, missing host, unresolvable host, or ANY resolved
        address that is loopback/private/link-local/etc.
    """
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https'):
        raise BlockedURL('Use an HTTP or HTTPS URL')
    host = parts.hostname
    if not host:
        raise BlockedURL('URL has no host')
    try:
        port = parts.port or (443 if parts.scheme == 'https' else 80)
    except ValueError:
        raise BlockedURL('URL has an invalid port')
    # A literal IP needs no DNS; checking it directly also covers decimal/odd forms the
    # resolver would otherwise normalise (e.g. 2130706433 is handled by getaddrinfo below).
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = list((resolver or _system_resolver)(host, port))
        except OSError as exc:
            raise BlockedURL('Host could not be resolved: ' + str(exc))
    if not addresses:
        raise BlockedURL('Host did not resolve to any address')
    for address in addresses:
        if not address_is_public(address):
            raise BlockedURL('Refusing to fetch a loopback, private or link-local address')
