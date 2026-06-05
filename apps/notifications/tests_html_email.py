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

    def _html_body(self):
        msg = mail.outbox[-1]
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

    def test_send_falls_back_to_plain_text_when_no_html_template(self):
        """Pokud HTML šablona neexistuje, odešle se e-mail jen v plain textu."""
        from apps.notifications.email import _send
        _send(
            subject='Test fallback',
            template='emails/assigned_to_you.txt',  # nemá HTML protějšek
            context={},
            recipients=['fallback@test.cz'],
        )
        self.assertGreater(len(mail.outbox), 0)
        msg = mail.outbox[0]
        self.assertTrue(msg.body)
        alternatives = getattr(msg, 'alternatives', [])
        html_alternatives = [c for c, m in alternatives if m == 'text/html']
        self.assertEqual(len(html_alternatives), 0, 'Neměla by existovat HTML alternativa')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='http://testserver',
    DEFAULT_FROM_EMAIL='helpdesk@test.cz',
)
class NewTicketHtmlTest(TestCase):

    def setUp(self):
        self.company, self.requester, self.ticket = _make_fixtures()

    def _html(self):
        from apps.notifications.email import send_new_ticket
        send_new_ticket(self.ticket)
        for content, mime in getattr(mail.outbox[-1], 'alternatives', []):
            if mime == 'text/html':
                return content
        return None

    def test_contains_ticket_title(self):
        self.assertIn('Testovací tiket', self._html())

    def test_contains_clickable_ticket_url(self):
        html = self._html()
        self.assertIn(f'/tickets/{self.ticket.pk}/', html)
        self.assertIn('<a ', html)

    def test_contains_description(self):
        self.assertIn('Krátký popis tiketu.', self._html())

    def test_truncates_long_description(self):
        self.ticket.description = 'B' * 400
        self.ticket.save()
        html = self._html()
        self.assertNotIn('B' * 400, html)
        self.assertIn('B' * 10, html)

    def test_contains_reply_token(self):
        self.assertIn(f'[#{self.ticket.pk}#]', self._html())


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='http://testserver',
    DEFAULT_FROM_EMAIL='helpdesk@test.cz',
)
class StatusChangeHtmlTest(TestCase):

    def setUp(self):
        from apps.tickets.models import Ticket as T
        self.company, self.requester, self.ticket = _make_fixtures()
        T.objects.filter(pk=self.ticket.pk).update(status=T.STATUS_IN_PROGRESS)
        self.ticket = T.objects.get(pk=self.ticket.pk)

    def _html(self):
        from apps.notifications.email import send_status_change
        send_status_change(self.ticket)
        for content, mime in getattr(mail.outbox[-1], 'alternatives', []):
            if mime == 'text/html':
                return content
        return None

    def test_contains_ticket_title(self):
        self.assertIn('Testovací tiket', self._html())

    def test_contains_new_status(self):
        self.assertIn('Řeší se', self._html())

    def test_contains_clickable_url(self):
        html = self._html()
        self.assertIn(f'/tickets/{self.ticket.pk}/', html)

    def test_contains_reply_token(self):
        self.assertIn(f'[#{self.ticket.pk}#]', self._html())


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='http://testserver',
    DEFAULT_FROM_EMAIL='helpdesk@test.cz',
)
class NewCommentHtmlTest(TestCase):

    def setUp(self):
        from apps.tickets.models import Comment
        self.company, self.requester, self.ticket = _make_fixtures()
        self.resolver = User.objects.create_user(
            username='resolver', email='resolver@test.cz', password='x'
        )
        UserRole.objects.create(user=self.resolver, role=UserRole.RESOLVER)
        self.comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.resolver,
            body='Komentář od řešitele.',
        )

    def _html(self):
        from apps.notifications.email import send_new_comment
        send_new_comment(self.comment)
        for content, mime in getattr(mail.outbox[-1], 'alternatives', []):
            if mime == 'text/html':
                return content
        return None

    def test_contains_ticket_title(self):
        self.assertIn('Testovací tiket', self._html())

    def test_contains_comment_body(self):
        self.assertIn('Komentář od řešitele.', self._html())

    def test_contains_author_name(self):
        self.assertIn('resolver', self._html())

    def test_contains_clickable_ticket_url(self):
        html = self._html()
        self.assertIn(f'/tickets/{self.ticket.pk}/', html)
        self.assertIn('<a ', html)

    def test_contains_reply_token(self):
        self.assertIn(f'[#{self.ticket.pk}#]', self._html())
