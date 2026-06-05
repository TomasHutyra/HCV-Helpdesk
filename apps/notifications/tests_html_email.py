"""
Testy HTML notifikačních e-mailů.

Spuštění:
    python manage.py test apps.notifications.tests_html_email --settings=helpdesk.settings.local
"""
from django.core import mail
from django.test import TestCase, override_settings

from apps.accounts.models import Company, User, UserRole
from apps.tickets.models import Area, Ticket


def _make_fixtures():
    """Vrátí (company, requester, ticket) pro testy."""
    company = Company.objects.create(name='Test firma')
    requester = User.objects.create_user(username='req', email='req@test.cz', password='x')
    requester.company = company
    requester.save()
    UserRole.objects.create(user=requester, role=UserRole.REQUESTER)
    area = Area.objects.create(name='IT')
    ticket = Ticket.objects.create(
        type=Ticket.TYPE_PROBLEM,
        title='Testovací tiket',
        description='Krátký popis tiketu.',
        area=area,
        priority=Ticket.PRIORITY_MEDIUM,
        company=company,
        requester=requester,
    )
    return company, requester, ticket


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='http://testserver',
    DEFAULT_FROM_EMAIL='helpdesk@test.cz',
)
class SendInfrastructureTest(TestCase):
    """Testy, že _send() připojí HTML alternativu pokud šablona existuje."""

    def _html_body(self, index=0):
        msg = mail.outbox[index]
        for content, mime in getattr(msg, 'alternatives', []):
            if mime == 'text/html':
                return content
        return None

    def test_send_new_ticket_has_html_alternative(self):
        """send_new_ticket odešle e-mail s HTML alternativou."""
        from apps.notifications.email import send_new_ticket
        _, _, ticket = _make_fixtures()
        send_new_ticket(ticket)
        self.assertGreater(len(mail.outbox), 0)
        self.assertIsNotNone(
            self._html_body(), 'E-mail neobsahuje HTML alternativu'
        )

    def test_send_new_ticket_plain_text_still_present(self):
        """Plain-text body zůstává — HTML je jen přidáno jako alternativa."""
        from apps.notifications.email import send_new_ticket
        _, _, ticket = _make_fixtures()
        send_new_ticket(ticket)
        msg = mail.outbox[0]
        self.assertTrue(msg.body, 'Plain-text body je prázdné')
