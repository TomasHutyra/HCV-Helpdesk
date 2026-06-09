"""
Testy pro IMAP polling — zejména _strip_quoted_text().

Spuštění:
    python manage.py test apps.notifications.tests_imap --settings=helpdesk.settings.local
"""
from django.test import SimpleTestCase

from apps.notifications.imap_polling import _strip_quoted_text


class StripQuotedTextTest(SimpleTestCase):

    def test_plain_reply_untouched(self):
        body = 'Potřebuji pomoc s přihlášením.'
        self.assertEqual(_strip_quoted_text(body), body)

    def test_gmail_greater_than_prefix(self):
        body = 'Nový text.\n\n> On Mon wrote:\n> Původní zpráva'
        self.assertEqual(_strip_quoted_text(body), 'Nový text.')

    def test_outlook_from_sent_header_en(self):
        body = 'Nový text.\n\nFrom: HCV Helpdesk <helpdesk@hcv.cz>\nSent: Monday, 9 June 2026'
        self.assertEqual(_strip_quoted_text(body), 'Nový text.')

    def test_outlook_from_sent_header_cz(self):
        body = 'Nový text.\n\nOd: HCV Helpdesk <helpdesk@hcv.cz>\nOdesláno: pondělí 9. června 2026'
        self.assertEqual(_strip_quoted_text(body), 'Nový text.')

    def test_original_message_separator(self):
        body = 'Nový text.\n\n-----Original Message-----\nStarý obsah'
        self.assertEqual(_strip_quoted_text(body), 'Nový text.')

    def test_outlook_mac_html_quote_with_new_text(self):
        """Outlook for Mac vkládá HTML zdroj citované zprávy do plain-text části."""
        body = (
            'Podívám se na to zítra.\n\n'
            '<html xmlns:v="urn:schemas-microsoft-com:vml"\n'
            'xmlns:o="urn:schemas-microsoft-com:office:office">\n'
            '<head><style>/* font definitions */</style></head>\n'
            '<body>původní obsah</body></html>'
        )
        self.assertEqual(_strip_quoted_text(body), 'Podívám se na to zítra.')

    def test_outlook_mac_html_quote_no_new_text(self):
        """Pokud odpověď neobsahuje žádný nový text, vrátí prázdný řetězec."""
        body = (
            '<html xmlns:v="urn:schemas-microsoft-com:vml">\n'
            '<head></head><body>původní obsah</body></html>'
        )
        self.assertEqual(_strip_quoted_text(body), '')

    def test_doctype_html_quote(self):
        body = 'OK, provedu to.\n\n<!DOCTYPE html><html><body>citace</body></html>'
        self.assertEqual(_strip_quoted_text(body), 'OK, provedu to.')

    def test_empty_body(self):
        self.assertEqual(_strip_quoted_text(''), '')

    def test_earliest_cut_wins(self):
        """Pokud jsou přítomny oba vzory, vyhraje ten s nižším indexem."""
        body = (
            'Text.\n\n'
            '<html><body>HTML citace</body></html>\n\n'
            'From: Someone\nSent: Monday'
        )
        self.assertEqual(_strip_quoted_text(body), 'Text.')
