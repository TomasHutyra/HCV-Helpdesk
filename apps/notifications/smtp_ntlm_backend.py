"""SMTP backend with NTLM auth for Microsoft Exchange.

Includes a pure-Python MD4 implementation so it works on systems where
OpenSSL has the legacy provider disabled (e.g. Ubuntu 24.04 / Python 3.12).
"""

import base64
import hashlib
import smtplib
import struct

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


# ---------------------------------------------------------------------------
# Pure Python MD4 (RFC 1320)
# ---------------------------------------------------------------------------

def _md4(data: bytes) -> bytes:
    def F(x, y, z): return (x & y) | (~x & z)
    def G(x, y, z): return (x & y) | (x & z) | (y & z)
    def H(x, y, z): return x ^ y ^ z
    def rol(x, n): return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF
    def add(*a): return sum(a) & 0xFFFFFFFF

    buf = bytearray(data)
    buf.append(0x80)
    while len(buf) % 64 != 56:
        buf.append(0)
    buf += struct.pack('<Q', len(data) * 8)

    A, B, C, D = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476

    R1_S = [3, 7, 11, 19]
    R2_K = [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]
    R2_S = [3, 5, 9, 13]
    R3_K = [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]
    R3_S = [3, 9, 11, 15]

    for i in range(0, len(buf), 64):
        X = list(struct.unpack('<16I', buf[i:i + 64]))
        a, b, c, d = A, B, C, D

        for j in range(16):
            a = rol(add(a, F(b, c, d), X[j]), R1_S[j % 4])
            a, b, c, d = d, a, b, c

        for j in range(16):
            a = rol(add(a, G(b, c, d), X[R2_K[j]], 0x5A827999), R2_S[j % 4])
            a, b, c, d = d, a, b, c

        for j in range(16):
            a = rol(add(a, H(b, c, d), X[R3_K[j]], 0x6ED9EBA1), R3_S[j % 4])
            a, b, c, d = d, a, b, c

        A, B, C, D = add(A, a), add(B, b), add(C, c), add(D, d)

    return struct.pack('<4I', A, B, C, D)


class _PureMD4:
    name = 'md4'
    digest_size = 16
    block_size = 64

    def __init__(self, data: bytes = b''):
        self._buf = bytearray(data)

    def update(self, data: bytes) -> None:
        self._buf += data

    def digest(self) -> bytes:
        return _md4(bytes(self._buf))

    def hexdigest(self) -> str:
        return self.digest().hex()

    def copy(self):
        c = _PureMD4()
        c._buf = bytearray(self._buf)
        return c


# Patch hashlib.new so ntlm_auth can use MD4 without the OpenSSL legacy provider.
_orig_hashlib_new = hashlib.new


def _patched_hashlib_new(name, *args, **kwargs):
    if name.lower() in ('md4', 'md-4'):
        kwargs.pop('usedforsecurity', None)
        data = args[0] if args else kwargs.get('data', kwargs.get('string', b''))
        return _PureMD4(data)
    return _orig_hashlib_new(name, *args, **kwargs)


hashlib.new = _patched_hashlib_new


# ---------------------------------------------------------------------------
# NTLM email backend
# ---------------------------------------------------------------------------

class NTLMEmailBackend(EmailBackend):
    """Django SMTP backend with NTLM authentication (Microsoft Exchange)."""

    def open(self):
        if self.connection:
            return False
        connection_params = {'local_hostname': DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            if not self.use_ssl and self.use_tls:
                self.connection.ehlo()
                self.connection.starttls()
                self.connection.ehlo()
            if self.username and self.password:
                self._ntlm_login()
            return True
        except OSError:
            if not self.fail_silently:
                raise

    def _ntlm_login(self):
        from ntlm_auth.ntlm import NtlmContext
        ctx = NtlmContext(self.username, self.password, '', '', ntlm_compatibility=3)

        negotiate = ctx.step()

        # Some Exchange servers reject inline negotiate — try two-step first
        code, resp = self.connection.docmd('AUTH', 'NTLM')
        if code == 334:
            code, resp = self.connection.docmd(base64.b64encode(negotiate).decode())
        else:
            code, resp = self.connection.docmd('AUTH', 'NTLM ' + base64.b64encode(negotiate).decode())

        if code != 334:
            raise smtplib.SMTPAuthenticationError(code, resp)

        challenge = base64.b64decode(resp)
        authenticate = ctx.step(challenge)
        code, resp = self.connection.docmd(base64.b64encode(authenticate).decode())
        if code != 235:
            raise smtplib.SMTPAuthenticationError(code, resp)
