"""
Funkce pro odesílání e-mailových notifikací.
Volány z Celery tasků (tasks.py).
"""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _sanitize_subject(subject):
    """Odstraní znaky nového řádku z předmětu e-mailu (prevence header injection)."""
    return subject.replace('\r', '').replace('\n', ' ')


def _ticket_token(ticket_id):
    return f'[#{ticket_id}#]'


def _send(subject, template, context, recipients, ticket_id=None):
    """Odešle e-mail na seznam příjemců. Chyby loguje, ale nevyhazuje výjimku."""
    if not recipients:
        return
    if ticket_id:
        subject = f'{subject} {_ticket_token(ticket_id)}'
        context = {**context, 'reply_ticket_id': ticket_id}
    body = render_to_string(template, context)
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info('E-mail "%s" odeslán na: %s', subject, recipients)
    except Exception as exc:
        logger.error('Chyba při odesílání e-mailu "%s": %s', subject, exc)


def _get_notifiable_managers(ticket):
    """
    Vrátí seznam e-mailů správců, kteří mají dostat notifikaci o tiketu,
    s respektováním jejich omezení na oblast a firmy.
    """
    from apps.accounts.models import User, UserRole
    managers = User.objects.filter(
        user_roles__role=UserRole.MANAGER, is_active=True
    ).prefetch_related('managed_companies')
    return [m.email for m in managers if m.can_see_ticket_as_manager(ticket)]


def send_new_ticket(ticket):
    """Nový tiket → žadateli + oprávněným správcům."""
    managers = _get_notifiable_managers(ticket)
    recipients = list({ticket.requester.email} | set(managers))

    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový tiket #{ticket.pk}: {ticket.title}'),
        template='emails/new_ticket.txt',
        context={'ticket': ticket},
        recipients=recipients,
        ticket_id=ticket.pk,
    )


def send_status_change(ticket):
    """Změna stavu na Řeší se nebo Příprava nabídky → žadateli."""
    _send(
        subject=f'[HCV Helpdesk] Stav tiketu #{ticket.pk} změněn: {ticket.get_status_display()}',
        template='emails/status_change.txt',
        context={'ticket': ticket},
        recipients=[ticket.requester.email],
        ticket_id=ticket.pk,
    )


def send_new_comment(comment):
    """Nový komentář → všem přiřazeným osobám (kromě autora komentáře)."""
    ticket = comment.ticket
    recipients_set = {ticket.requester.email}
    if ticket.resolver:
        recipients_set.add(ticket.resolver.email)
    if ticket.sales:
        recipients_set.add(ticket.sales.email)
    recipients_set.discard(comment.author.email)

    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový komentář k tiketu #{ticket.pk}: {ticket.title}'),
        template='emails/new_comment.txt',
        context={'ticket': ticket, 'comment': comment},
        recipients=list(recipients_set),
        ticket_id=ticket.pk,
    )


def send_assigned_to_you(ticket, assignee):
    """Přiřazení řešitele nebo obchodníka → notifikace přiřazené osobě."""
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Byl vám přiřazen tiket #{ticket.pk}: {ticket.title}'),
        template='emails/assigned_to_you.txt',
        context={'ticket': ticket},
        recipients=[assignee.email],
        ticket_id=ticket.pk,
    )


def send_ticket_closed(ticket, closed_as):
    """Vyřešení nebo zamítnutí → žadateli."""
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Tiket #{ticket.pk} {ticket.get_status_display()}: {ticket.title}'),
        template='emails/ticket_closed.txt',
        context={'ticket': ticket, 'closed_as': closed_as},
        recipients=[ticket.requester.email],
        ticket_id=ticket.pk,
    )
    if closed_as == 'resolved':
        send_rating_request(ticket)


def send_rating_request(ticket):
    """Výzva k hodnocení → výhradně žadateli (HTML e-mail s klikatelnými hvězdičkami)."""
    site_url = settings.SITE_URL.rstrip('/')
    rating_options = [
        {
            'score': score,
            'url': site_url + reverse('tickets:rate', args=[ticket.pk, ticket.rating_token, score]),
            'stars': '★' * score + '☆' * (5 - score),
        }
        for score in range(6)
    ]
    subject = _sanitize_subject(f'[HCV Helpdesk] Ohodnoťte řešení tiketu #{ticket.pk}: {ticket.title}')
    context = {'ticket': ticket, 'rating_options': rating_options}
    text_body = render_to_string('emails/rating_request.txt', context)
    html_body = render_to_string('emails/rating_request.html', context)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[ticket.requester.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    try:
        msg.send()
        logger.info('Rating request odeslán na: %s', ticket.requester.email)
    except Exception as exc:
        logger.error('Chyba při odesílání rating request "%s": %s', subject, exc)
