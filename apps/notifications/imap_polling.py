"""
IMAP polling — čte nové e-maily a zakládá tikety.

Spouštěno přes Celery Beat každé 2 minuty (tasks.poll_imap_inbox).
Lokálně (CELERY_TASK_ALWAYS_EAGER=True) lze volat přímo pro testování.
"""
import email
import logging
import os
import re
from email.header import decode_header, make_header

from django.conf import settings
from django.core.files.base import ContentFile

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


def _find_requester_by_email(from_email):
    """Najde uživatele s rolí Žadatel podle e-mailové adresy (pro vytváření tiketů)."""
    from apps.accounts.models import User, UserRole
    try:
        return User.objects.get(email__iexact=from_email, user_roles__role=UserRole.REQUESTER, is_active=True)
    except User.DoesNotExist:
        return None


def _find_any_user_by_email(from_email):
    """Najde libovolného aktivního uživatele podle e-mailové adresy (pro odpovědi)."""
    from apps.accounts.models import User
    try:
        return User.objects.get(email__iexact=from_email, is_active=True)
    except User.DoesNotExist:
        return None


_TICKET_TOKEN_RE = re.compile(r'\[#(\d+)#\]')


def _extract_ticket_id(subject, body):
    """Extrahuje ID tiketu z tokenu [#42#] v předmětu nebo těle e-mailu.

    Vrátí ID (int), nebo None pokud token chybí nebo jsou ID neshodná.
    Pro rozlišení mismatche od absence tokenu použij _has_token_mismatch().
    """
    m_subject = _TICKET_TOKEN_RE.search(subject)
    m_body = _TICKET_TOKEN_RE.search(body)
    id_subject = int(m_subject.group(1)) if m_subject else None
    id_body = int(m_body.group(1)) if m_body else None
    if id_subject is not None and id_body is not None and id_subject != id_body:
        return None
    return id_subject if id_subject is not None else id_body


def _has_token_mismatch(subject, body):
    """Vrátí True, pokud jsou tokeny v předmětu i těle přítomny, ale neshodují se."""
    m_subject = _TICKET_TOKEN_RE.search(subject)
    m_body = _TICKET_TOKEN_RE.search(body)
    if m_subject is None or m_body is None:
        return False
    return int(m_subject.group(1)) != int(m_body.group(1))


_QUOTE_HEADER_RE = re.compile(
    r'^(On |Dne |Am |Le |El ).{5,100}(wrote:|napsal[a]?:|schrieb:|a écrit:|escribió:)\s*$',
    re.IGNORECASE | re.MULTILINE,
)
_ORIGINAL_MSG_RE = re.compile(r'^-{3,}[^-\r\n]', re.MULTILINE)
# Zachytí "-----Original Message-----", "---------- Původní e‑mail ----------" apod.
# Nezachytí holou oddělovací čáru "------..." (bez textu).

_OUTLOOK_HEADER_RE = re.compile(
    r'^(From|Od|De|Van): .+\r?\n(Sent|Odesláno|Envoyé|Verzonden): ',
    re.MULTILINE,
)
# Zachytí Outlook reply header ve formátu "From: ...\nSent: ..." (EN, CZ, FR, NL).


def _strip_quoted_text(body):
    """Odstraní citovaný text z odpovědi, ponechá pouze nový obsah."""
    cut = len(body)
    for pattern in (
        re.compile(r'^>.*$', re.MULTILINE),
        _QUOTE_HEADER_RE,
        _ORIGINAL_MSG_RE,
        _OUTLOOK_HEADER_RE,
    ):
        m = pattern.search(body)
        if m:
            cut = min(cut, m.start())
    return body[:cut].strip()


def _can_add_email_comment(user, ticket):
    """Vrátí True, pokud smí uživatel přidat komentář k tiketu přes e-mail."""
    from apps.accounts.models import UserRole
    from apps.tickets.models import Ticket
    is_closed = ticket.status in (Ticket.STATUS_RESOLVED, Ticket.STATUS_REJECTED)
    if user.has_role(UserRole.ADMIN):
        return True
    if user.has_role(UserRole.MANAGER):
        return user.can_see_ticket_as_manager(ticket)
    if is_closed:
        return user.has_role(UserRole.REQUESTER) and ticket.requester == user
    if user.has_role(UserRole.REQUESTER):
        return ticket.requester == user
    if user.has_role(UserRole.RESOLVER):
        return ticket.resolver == user
    if user.has_role(UserRole.SALES):
        return ticket.sales == user
    return False


def _process_reply(ticket_id, raw_body, sender_user, attachments, original_subject=''):
    """Zpracuje příchozí odpověď na notifikaci a přidá ji jako komentář k tiketu."""
    from apps.tickets.models import Ticket, Comment
    try:
        ticket = Ticket.objects.get(pk=ticket_id)
    except Ticket.DoesNotExist:
        logger.warning('Tiket #%s neexistuje — odpověď ignorována.', ticket_id)
        _send_rejection_notice(
            sender_user.email, original_subject,
            f'Tiket #{ticket_id} nebyl nalezen.',
        )
        return
    if not _can_add_email_comment(sender_user, ticket):
        logger.warning('Uživatel %s nemá oprávnění komentovat tiket #%s.', sender_user.email, ticket_id)
        _send_rejection_notice(
            sender_user.email, original_subject,
            f'Nemáte oprávnění přidat komentář k tiketu #{ticket_id}.',
        )
        return
    body = _strip_quoted_text(raw_body)
    if not body:
        logger.warning('Prázdné tělo odpovědi od %s k tiketu #%s — ignorováno.', sender_user.email, ticket_id)
        _send_rejection_notice(
            sender_user.email, original_subject,
            'E-mail neobsahoval žádný text (obsahoval pouze citovanou zprávu).',
        )
        return
    comment = Comment.objects.create(ticket=ticket, author=sender_user, body=body)
    logger.info('Vytvořen komentář #%s k tiketu #%s z e-mailu od %s.', comment.pk, ticket_id, sender_user.email)
    if attachments:
        _save_attachments(ticket, sender_user, attachments)
    from apps.notifications.tasks import notify_new_comment
    notify_new_comment.delay(comment.pk)


def _is_duplicate(message_id):
    """Vrátí True, pokud jsme tento Message-ID již zpracovali (TTL 30 dní)."""
    if not message_id:
        return False
    from django.core.cache import cache
    key = f'imap_msgid:{message_id}'
    if cache.get(key):
        return True
    cache.set(key, 1, timeout=60 * 60 * 24 * 30)
    return False


def _is_rate_limited(from_email):
    """Vrátí True, pokud odesílatel překročil limit tiketů za hodinu."""
    from django.conf import settings
    from django.core.cache import cache
    limit = getattr(settings, 'IMAP_RATE_LIMIT', 10)
    key = f'imap_rl:{from_email.lower()}'
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=3600)
    return False


def _should_send_rate_limit_notice(from_email):
    """Vrátí True (a zároveň příznak nastaví) pouze pro první zamítnutí v daném okně.

    Zabraňuje opakovanému zasílání notifikací při překročení rate limitu.
    """
    from django.core.cache import cache
    key = f'imap_rl_notif:{from_email.lower()}'
    if cache.get(key):
        return False
    cache.set(key, 1, timeout=3600)
    return True


def _send_rejection_notice(to_email, original_subject, reason):
    """Odešle odesílateli automatickou odpověď s důvodem zamítnutí e-mailu."""
    from django.conf import settings
    from django.core.mail import send_mail
    subject = f'Re: {original_subject}' if original_subject else '[HCV Helpdesk] E-mail nebyl zpracován'
    body = (
        'Váš e-mail nebyl systémem HCV Helpdesk zpracován.\n\n'
        f'Důvod: {reason}\n\n'
        '---\n'
        'Tato zpráva byla vygenerována automaticky. Neodpovídejte na ni.'
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        logger.info('Zamítnutí odesláno na %s: %s', to_email, reason)
    except Exception as exc:
        logger.error('Chyba při odesílání zamítnutí na %s: %s', to_email, exc)


def _get_attachments(msg):
    """Vrátí seznam (filename, content_bytes) pro přílohy e-mailu.

    Přeskočí části bez Content-Disposition attachment nebo inline bez názvu,
    a části text/plain a text/html (to je tělo zprávy).
    """
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        content_disposition = part.get('Content-Disposition', '')
        content_type = part.get_content_type()
        # Přeskočit textové části těla zprávy
        if content_type in ('text/plain', 'text/html') and 'attachment' not in content_disposition:
            continue
        # Zpracovat pouze části s názvem souboru
        filename = part.get_filename()
        if not filename:
            continue
        filename = str(make_header(decode_header(filename)))
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        attachments.append((filename, payload))
    return attachments


def _save_attachments(ticket, requester, attachments):
    """Uloží přílohy e-mailu jako TicketAttachment záznamy.

    Přeskočí soubory s nepovolenou příponou nebo příliš velké (stejná pravidla
    jako při ručním uploadu).
    """
    from apps.tickets.models import TicketAttachment, TicketChange, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE
    for filename, content in attachments:
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext not in ALLOWED_EXTENSIONS:
            logger.warning('Příloha "%s" má nepovolenou příponu, přeskočena.', filename)
            continue
        if len(content) > MAX_UPLOAD_SIZE:
            logger.warning('Příloha "%s" překračuje 5 MB limit, přeskočena.', filename)
            continue
        att = TicketAttachment(ticket=ticket, original_name=filename, uploaded_by=requester)
        att.file.save(filename, ContentFile(content), save=True)
        TicketChange.objects.create(
            ticket=ticket,
            user=requester,
            field=TicketChange.FIELD_ATTACHMENT_ADDED,
            old_value='',
            new_value=filename,
        )
        logger.info('Uložena příloha "%s" k tiketu #%s.', filename, ticket.pk)


def _create_ticket_from_email(subject, body, requester, attachments):
    from apps.tickets.models import Ticket, Area
    ticket = Ticket.objects.create(
        type=Ticket.TYPE_PROBLEM,
        title=subject[:200] or '(bez předmětu)',
        description=body or '(prázdné tělo e-mailu)',
        area=Area.get_unknown(),
        priority=Ticket.PRIORITY_MEDIUM,
        company=requester.company,
        requester=requester,
    )
    logger.info('Vytvořen tiket #%s z e-mailu od %s', ticket.pk, requester.email)
    if attachments:
        _save_attachments(ticket, requester, attachments)
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
            message_id = msg.get('Message-ID', '').strip()

            # Deduplikace — přeskočit e-mail, který už byl zpracován
            if _is_duplicate(message_id):
                logger.info('Přeskočen duplicitní e-mail Message-ID=%s', message_id)
                server.add_flags(uid, [imapclient.SEEN])
                continue

            body = _get_body(msg)

            if _has_token_mismatch(subject, body):
                logger.warning('Token mismatch v e-mailu od %s — ignorováno.', from_email)
                user = _find_any_user_by_email(from_email)
                if user is not None:
                    _send_rejection_notice(
                        from_email, subject,
                        'E-mail obsahuje nekonzistentní identifikátor tiketu '
                        '(číslo tiketu v předmětu a těle zprávy se neshoduje).',
                    )
                server.add_flags(uid, [imapclient.SEEN])
                continue

            ticket_id = _extract_ticket_id(subject, body)

            if ticket_id is not None:
                # Odpověď na notifikaci → nový komentář
                user = _find_any_user_by_email(from_email)
                if user is None:
                    logger.warning('Neznámý odesílatel %s — odpověď ignorována.', from_email)
                    server.add_flags(uid, [imapclient.SEEN])
                    continue
                if _is_rate_limited(from_email):
                    logger.warning('Rate limit překročen pro %s — odpověď ignorována.', from_email)
                    if _should_send_rate_limit_notice(from_email):
                        limit = getattr(settings, 'IMAP_RATE_LIMIT', 10)
                        _send_rejection_notice(
                            from_email, subject,
                            f'Byl překročen hodinový limit pro odesílání e-mailů ({limit}/hod). '
                            'Zkuste to prosím za hodinu.',
                        )
                    server.add_flags(uid, [imapclient.SEEN])
                    continue
                attachments = _get_attachments(msg)
                _process_reply(ticket_id, body, user, attachments, original_subject=subject)
            else:
                # Nový e-mail bez tokenu → nový tiket
                requester = _find_requester_by_email(from_email)
                if requester is None:
                    logger.warning('Neznámý odesílatel nebo chybějící role Žadatel: %s — tiket nevytvořen.', from_email)
                    user = _find_any_user_by_email(from_email)
                    if user is not None:
                        _send_rejection_notice(
                            from_email, subject,
                            'Nemáte oprávnění zakládat tikety prostřednictvím e-mailu. '
                            'Tato funkce je dostupná pouze pro uživatele s rolí Žadatel.',
                        )
                    server.add_flags(uid, [imapclient.SEEN])
                    continue
                if _is_rate_limited(from_email):
                    logger.warning('Rate limit překročen pro %s — tiket nevytvořen.', from_email)
                    if _should_send_rate_limit_notice(from_email):
                        limit = getattr(settings, 'IMAP_RATE_LIMIT', 10)
                        _send_rejection_notice(
                            from_email, subject,
                            f'Byl překročen hodinový limit pro odesílání e-mailů ({limit}/hod). '
                            'Zkuste to prosím za hodinu.',
                        )
                    server.add_flags(uid, [imapclient.SEEN])
                    continue
                attachments = _get_attachments(msg)
                _create_ticket_from_email(subject, body, requester, attachments)

            server.add_flags(uid, [imapclient.SEEN])

        server.logout()

    except Exception as exc:
        logger.error('Chyba při IMAP pollingu: %s', exc)
