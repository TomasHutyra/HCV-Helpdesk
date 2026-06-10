"""
Testy pro password reset flow.

Spuštění:
    python manage.py test apps.accounts.tests_password_reset --settings=helpdesk.settings.local
"""
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class PasswordResetUrlsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.cz', password='starehe slo123'
        )

    def test_reset_form_page_accessible(self):
        """Stránka pro zadání e-mailu vrátí 200."""
        response = self.client.get(reverse('accounts:password_reset'))
        self.assertEqual(response.status_code, 200)

    def test_reset_done_page_accessible(self):
        """Potvrzovací stránka vrátí 200."""
        response = self.client.get(reverse('accounts:password_reset_done'))
        self.assertEqual(response.status_code, 200)

    def test_reset_complete_page_accessible(self):
        """Stránka úspěchu vrátí 200."""
        response = self.client.get(reverse('accounts:password_reset_complete'))
        self.assertEqual(response.status_code, 200)

    def test_post_existing_email_sends_mail(self):
        """POST s existujícím e-mailem odešle reset e-mail."""
        self.client.post(reverse('accounts:password_reset'), {'email': 'test@example.cz'})
        self.assertEqual(len(mail.outbox), 1)

    def test_post_nonexistent_email_sends_no_mail(self):
        """POST s neexistujícím e-mailem tiše neodešle nic."""
        self.client.post(reverse('accounts:password_reset'), {'email': 'neexistuje@example.cz'})
        self.assertEqual(len(mail.outbox), 0)

    def test_post_valid_email_redirects_to_done(self):
        """POST s platným e-mailem přesměruje na done stránku."""
        response = self.client.post(
            reverse('accounts:password_reset'), {'email': 'test@example.cz'}
        )
        self.assertRedirects(response, reverse('accounts:password_reset_done'))

    def test_reset_email_has_html_alternative(self):
        """Reset e-mail obsahuje HTML alternativu."""
        self.client.post(reverse('accounts:password_reset'), {'email': 'test@example.cz'})
        msg = mail.outbox[0]
        html_bodies = [c for c, mime in getattr(msg, 'alternatives', []) if mime == 'text/html']
        self.assertTrue(html_bodies, 'E-mail neobsahuje HTML alternativu')

    def test_reset_email_subject_contains_helpdesk(self):
        """Předmět reset e-mailu obsahuje HCV Helpdesk."""
        self.client.post(reverse('accounts:password_reset'), {'email': 'test@example.cz'})
        self.assertIn('HCV Helpdesk', mail.outbox[0].subject)

    def test_login_page_contains_reset_link(self):
        """Login stránka obsahuje odkaz na reset hesla."""
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, reverse('accounts:password_reset'))
