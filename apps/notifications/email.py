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


def _cc_emails(ticket):
    """Vrátí seznam CC příjemců tiketu (kontaktní osoba, pokud je vyplněna)."""
    if ticket.contact_person_email:
        return [ticket.contact_person_email]
    return []


def _ticket_token(ticket_id):
    return f'[#{ticket_id}#]'


def _send(subject, template, context, recipients, ticket_id=None, cc=None):
    """Odešle e-mail na seznam příjemců. Chyby loguje, ale nevyhazuje výjimku."""
    if not recipients:
        if not cc:
            return
        # Všichni primární příjemci byli vyřazeni (např. autor = jediný příjemce),
        # ale CC existuje — povýšíme CC na To, aby notifikace kontaktní osobě dorazila.
        recipients, cc = cc, []
    if ticket_id:
        subject = f'{subject} {_ticket_token(ticket_id)}'
        ticket_url = settings.SITE_URL.rstrip('/') + reverse('tickets:detail', args=[ticket_id])
        context = {**context, 'reply_ticket_id': ticket_id, 'ticket_url': ticket_url}
    body = render_to_string(template, context)
    try:
        from django.core.mail import EmailMessage
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
            cc=cc or [],
        )
        msg.send(fail_silently=False)
        logger.info('E-mail "%s" odeslán na: %s, CC: %s', subject, recipients, cc or [])
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


def _get_notifiable_resolvers(ticket):
    """
    Vrátí seznam e-mailů řešitelů s notify_new_ticket=True, kteří pokrývají oblast tiketu.
    Oblast Neznámá (is_unknown) nebo null → notifikace všem aktivním řešitelům s opt-in.
    """
    from apps.accounts.models import User, UserRole
    resolvers = User.objects.filter(
        user_roles__role=UserRole.RESOLVER,
        is_active=True,
        notify_new_ticket=True,
    ).prefetch_related('resolver_areas')
    return [r.email for r in resolvers if r.can_handle_ticket_area(ticket)]


def send_new_ticket(ticket):
    """Nový tiket → žadateli + oprávněným správcům + přihlášeným řešitelům."""
    managers = _get_notifiable_managers(ticket)
    resolvers = _get_notifiable_resolvers(ticket)
    recipients = list({ticket.requester.email} | set(managers) | set(resolvers))
    recipients_set = set(recipients)

    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový tiket #{ticket.pk}: {ticket.title}'),
        template='emails/new_ticket.txt',
        context={'ticket': ticket},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients_set],
    )


def send_status_change(ticket):
    """Změna stavu na Řeší se nebo Příprava nabídky → žadateli."""
    recipients = [ticket.requester.email]
    _send(
        subject=f'[HCV Helpdesk] Stav tiketu #{ticket.pk} změněn: {ticket.get_status_display()}',
        template='emails/status_change.txt',
        context={'ticket': ticket},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients],
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

    cc = [e for e in _cc_emails(ticket) if e not in recipients_set and e != comment.author.email]
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový komentář k tiketu #{ticket.pk}: {ticket.title}'),
        template='emails/new_comment.txt',
        context={'ticket': ticket, 'comment': comment},
        recipients=list(recipients_set),
        ticket_id=ticket.pk,
        cc=cc,
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
    recipients = [ticket.requester.email]
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Tiket #{ticket.pk} {ticket.get_status_display()}: {ticket.title}'),
        template='emails/ticket_closed.txt',
        context={'ticket': ticket, 'closed_as': closed_as},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients],
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
