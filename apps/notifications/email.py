"""
Funkce pro odesílání e-mailových notifikací.
Volány z Celery tasků (tasks.py).
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _send(subject, template, context, recipients):
    """Odešle e-mail na seznam příjemců. Chyby loguje, ale nevyhazuje výjimku."""
    if not recipients:
        return
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


def send_new_ticket(ticket):
    """Nový tiket → žadateli + všem správcům."""
    from apps.accounts.models import User, UserRole

    managers = list(
        User.objects.filter(user_roles__role=UserRole.MANAGER, is_active=True)
        .values_list('email', flat=True)
    )
    recipients = list({ticket.requester.email} | set(managers))

    _send(
        subject=f'[HCV Helpdesk] Nový tiket #{ticket.pk}: {ticket.title}',
        template='emails/new_ticket.txt',
        context={'ticket': ticket},
        recipients=recipients,
    )


def send_status_change(ticket):
    """Změna stavu na Řeší se nebo Příprava nabídky → žadateli."""
    _send(
        subject=f'[HCV Helpdesk] Stav tiketu #{ticket.pk} změněn: {ticket.get_status_display()}',
        template='emails/status_change.txt',
        context={'ticket': ticket},
        recipients=[ticket.requester.email],
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
        subject=f'[HCV Helpdesk] Nový komentář k tiketu #{ticket.pk}: {ticket.title}',
        template='emails/new_comment.txt',
        context={'ticket': ticket, 'comment': comment},
        recipients=list(recipients_set),
    )


def send_assigned_to_you(ticket, assignee):
    """Přiřazení řešitele nebo obchodníka → notifikace přiřazené osobě."""
    _send(
        subject=f'[HCV Helpdesk] Byl vám přiřazen tiket #{ticket.pk}: {ticket.title}',
        template='emails/assigned_to_you.txt',
        context={'ticket': ticket},
        recipients=[assignee.email],
    )


def send_ticket_closed(ticket, closed_as):
    """Vyřešení nebo zamítnutí → žadateli."""
    _send(
        subject=f'[HCV Helpdesk] Tiket #{ticket.pk} {ticket.get_status_display()}: {ticket.title}',
        template='emails/ticket_closed.txt',
        context={'ticket': ticket, 'closed_as': closed_as},
        recipients=[ticket.requester.email],
    )
