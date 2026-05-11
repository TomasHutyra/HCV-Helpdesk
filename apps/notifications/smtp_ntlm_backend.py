import base64
import smtplib

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


class NTLMEmailBackend(EmailBackend):
    """SMTP email backend with NTLM authentication (e.g. Microsoft Exchange)."""

    def open(self):
        if self.connection:
            return False
        connection_params = {'local_hostname': DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params.update({
                'keyfile': self.ssl_keyfile,
                'certfile': self.ssl_certfile,
            })
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
        ctx = NtlmContext(self.username, self.password, None, None, ntlm_compatibility=3)

        negotiate = ctx.step()
        code, resp = self.connection.docmd('AUTH', 'NTLM ' + base64.b64encode(negotiate).decode())
        if code != 334:
            raise smtplib.SMTPAuthenticationError(code, resp)

        challenge = base64.b64decode(resp)
        authenticate = ctx.step(challenge)
        code, resp = self.connection.docmd(base64.b64encode(authenticate).decode())
        if code != 235:
            raise smtplib.SMTPAuthenticationError(code, resp)
