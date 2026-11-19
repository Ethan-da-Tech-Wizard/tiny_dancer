# ==============================================================================
# tests/test_url_guard.py - SSRF guard for the fetch_json tool
#
# Pins down: (1) address_is_public / ensure_public_url classify loopback, private,
# link-local, mapped-IPv6 and mixed-DNS answers correctly; (2) retrieve_json refuses
# loopback targets and re-checks EVERY redirect hop (a public host redirecting to
# 127.0.0.1 or 169.254.169.254 must fail before the second request is sent).
#
# httpx is a runtime dependency but may be absent on a dev machine; when it is, a
# minimal stand-in exposing only the API retrieve_json uses (AsyncClient.stream, a
# response with status_code/headers/url/raise_for_status/aiter_bytes) is installed so
# the control flow is still exercised. With real httpx, httpx.MockTransport is used.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import sys
import tempfile
import types
import unittest

from app.url_guard import BlockedURL, address_is_public, ensure_public_url

try:
    import httpx
    REAL_HTTPX = True
except ImportError:
    REAL_HTTPX = False

    class _Resp:
        """Stand-in for httpx.Response with only what retrieve_json reads."""

        def __init__(self, status, headers, body, url):
            self.status_code, self.headers, self._body, self.url = status, headers, body, url

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError('HTTP %d' % self.status_code)

        async def aiter_bytes(self):
            yield self._body

    class _Stream:
        """Async context manager returned by AsyncClient.stream()."""

        def __init__(self, resp):
            self.resp = resp

        async def __aenter__(self):
            return self.resp

        async def __aexit__(self, *a):
            return False

    class _Client:
        """AsyncClient stand-in: the 'transport' is just a handler(url) -> (status, headers, body)."""

        def __init__(self, timeout=None, follow_redirects=None, transport=None):
            assert follow_redirects is False, 'redirects must be followed manually so each hop is checked'
            self.handler = transport

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def stream(self, method, url, headers=None):
            status, hdrs, body = self.handler(url)
            return _Stream(_Resp(status, hdrs, body, url))

    httpx = types.SimpleNamespace(AsyncClient=_Client)
    sys.modules['httpx'] = httpx

from app import facts  # noqa: E402  (must follow the optional httpx stand-in)


def transport_for(handler):
    """Build the `transport` argument: handler(url) -> (status, headers, body_bytes)."""
    if not REAL_HTTPX:
        return handler

    def real(request):
        status, headers, body = handler(str(request.url))
        return httpx.Response(status, headers=headers, content=body)
    return httpx.MockTransport(real)


class AddressTests(unittest.TestCase):
    """Classification of individual addresses."""

    # Scenario: every address class an attacker would aim at must be rejected, public ones allowed.
    def test_classification(self):
        for bad in ['127.0.0.1', '10.0.0.1', '172.16.5.5', '192.168.1.1', '169.254.169.254', '100.64.0.1',
                    '0.0.0.0', '224.0.0.1', '::1', 'fe80::1%en0', 'fc00::1', '::ffff:127.0.0.1', '::ffff:10.0.0.1']:
            self.assertFalse(address_is_public(bad), bad)
        for good in ['8.8.8.8', '93.184.216.34', '2606:4700::1111']:
            self.assertTrue(address_is_public(good), good)

    # Scenario: literal IPs, schemes, DNS answers (one private among public must refuse), no answer.
    def test_ensure_public_url(self):
        pub = lambda host, port: ['93.184.216.34']
        ensure_public_url('https://example.com/x', pub)
        for url in ['http://127.0.0.1:3210/api', 'http://[::1]/', 'http://169.254.169.254/latest/meta-data',
                    'http://192.168.0.1/', 'ftp://example.com/', 'file:///etc/passwd', 'http:///nohost']:
            with self.assertRaises(BlockedURL, msg=url):
                ensure_public_url(url, pub)
        with self.assertRaises(BlockedURL):
            ensure_public_url('https://rebind.example/', lambda h, p: ['93.184.216.34', '127.0.0.1'])
        with self.assertRaises(BlockedURL):
            ensure_public_url('https://nothing.example/', lambda h, p: [])

        def failing(host, port):
            raise OSError('no such host')
        with self.assertRaises(BlockedURL):
            ensure_public_url('https://nx.example/', failing)


class RetrieveJsonTests(unittest.TestCase):
    """retrieve_json end to end against a scripted transport."""

    def run_fetch(self, url, handler):
        with tempfile.TemporaryDirectory() as tmp:
            return asyncio.run(facts.retrieve_json(url, tmp, transport_for(handler)))

    # Scenario: a normal public URL still works and returns the parsed JSON.
    def test_public_url_ok(self):
        data, meta = self.run_fetch('https://example.com/data', lambda u: (200, {}, b'{"a": 1}'))
        self.assertEqual(data, {'a': 1})
        self.assertEqual(meta['http_status'], 200)

    # Scenario: the model asks for this app's own API; refused before any request is made.
    def test_loopback_refused_without_request(self):
        calls = []

        def handler(u):
            calls.append(u)
            return 200, {}, b'{}'
        with self.assertRaises(ValueError):
            self.run_fetch('http://127.0.0.1:3210/api/sessions', handler)
        self.assertEqual(calls, [])

    # Scenario: a public page redirects to loopback / cloud metadata; the second request must never be sent.
    def test_redirect_to_private_refused(self):
        for target in ['http://127.0.0.1:3210/api/status', 'http://169.254.169.254/latest/meta-data/', '/../../x']:
            calls = []

            def handler(u, target=target, calls=calls):
                calls.append(u)
                if len(calls) == 1:
                    return 302, {'location': target}, b''
                return 200, {}, b'{"secret": true}'
            if target.startswith('/'):
                # Relative redirect stays on the public host: allowed.
                data, _ = self.run_fetch('https://example.com/a', handler)
                self.assertEqual(data, {'secret': True})
                continue
            with self.assertRaises(ValueError):
                self.run_fetch('https://example.com/a', handler)
            self.assertEqual(calls, ['https://example.com/a'], target)

    # Scenario: a redirect loop ends with an error instead of hanging.
    def test_too_many_redirects(self):
        with self.assertRaises(ValueError):
            self.run_fetch('https://example.com/a', lambda u: (302, {'location': 'https://example.com/b'}, b''))


if __name__ == '__main__':
    unittest.main()
