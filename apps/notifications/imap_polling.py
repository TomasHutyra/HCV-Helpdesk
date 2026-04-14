"""
IMAP polling — čte nové e-maily a zakládá tikety.

Spouštěno přes Celery Beat každé 2 minuty (tasks.poll_imap_inbox).
Lokálně (CELERY_TASK_ALWAYS_EAGER=True) lze volat přímo pro testování.
"""
import email
import logging
from email.header import decode_header, make_header

from django.conf import settings

logger = logging.getLogger(__name__)


def _decode_header(value):
    """Dekóduje e-mailový header (může být base64/QP kódovaný)."""
    if not value:
        return ''
    return str(make_header(decode_header(value)))


def _get_body(msg):
    """Extrahuje textové tělo e-mailu (plain text preferováno)."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='replace')
    return body.strip()


def _find_user_by_email(from_email):
    """Najde uživatele s rolí Žadatel podle e-mailové adresy."""
    from apps.accounts.models import User, UserRole
    try:
        return User.objects.get(email__iexact=from_email, user_roles__role=UserRole.REQUESTER, is_active=True)
    except User.DoesNotExist:
        return None


def _create_ticket_from_email(subject, body, requester):
    from apps.tickets.models import Ticket
    ticket = Ticket.objects.create(
        type=Ticket.TYPE_PROBLEM,
        title=subject[:200] or '(bez předmětu)',
        description=body or '(prázdné tělo e-mailu)',
        area=Ticket.AREA_UNKNOWN,
        priority=Ticket.PRIORITY_MEDIUM,
        company=requester.company,
        requester=requester,
    )
    logger.info('Vytvořen tiket #%s z e-mailu od %s', ticket.pk, requester.email)
    # Odeslat notifikaci
    from apps.notifications.tasks import notify_new_ticket
    notify_new_ticket.delay(ticket.pk)
    return ticket


def process_inbox():
    """Připojí se na IMAP, přečte nepřečtené e-maily a zpracuje je."""
    host = settings.IMAP_HOST
    if not host:
        logger.debug('IMAP není nakonfigurován, přeskakuji polling.')
        return

    try:
        import imapclient
        ssl = settings.IMAP_USE_SSL
        server = imapclient.IMAPClient(
            host=host,
            port=settings.IMAP_PORT,
            ssl=ssl,
            use_uid=True,
        )
        server.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        server.select_folder(settings.IMAP_FOLDER)

        messages_ids = server.search(['UNSEEN'])
        if not messages_ids:
            server.logout()
            return

        fetch_data = server.fetch(messages_ids, ['RFC822', 'FLAGS'])
        for uid, data in fetch_data.items():
            raw = data[b'RFC822']
            msg = email.message_from_bytes(raw)

            from_field = _decode_header(msg.get('From', ''))
            # Extrahovat samotnou e-mailovou adresu
            from email.utils import parseaddr
            _, from_email = parseaddr(from_field)
            subject = _decode_header(msg.get('Subject', ''))
            body = _get_body(msg)

            requester = _find_user_by_email(from_email)
            if requester is None:
                logger.warning('Neznámý odesílatel: %s — tiket nevytvořen.', from_email)
                # Přesto označit jako přečtený, aby se znovu nezpracoval
                server.set_flags(uid, [imapclient.SEEN])
                continue

            _create_ticket_from_email(subject, body, requester)
            server.set_flags(uid, [imapclient.SEEN])

        server.logout()

    except Exception as exc:
        logger.error('Chyba při IMAP pollingu: %s', exc)
