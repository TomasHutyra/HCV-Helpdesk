from celery import shared_task


@shared_task
def notify_new_ticket(ticket_pk):
    from apps.tickets.models import Ticket
    from .email import send_new_ticket
    try:
        ticket = Ticket.objects.select_related('requester', 'company').get(pk=ticket_pk)
        send_new_ticket(ticket)
    except Ticket.DoesNotExist:
        pass


@shared_task
def notify_status_change(ticket_pk):
    from apps.tickets.models import Ticket
    from .email import send_status_change
    try:
        ticket = Ticket.objects.select_related('requester').get(pk=ticket_pk)
        send_status_change(ticket)
    except Ticket.DoesNotExist:
        pass


@shared_task
def notify_new_comment(comment_pk):
    from apps.tickets.models import Comment
    from .email import send_new_comment
    try:
        comment = Comment.objects.select_related('ticket__requester', 'ticket__resolver', 'ticket__sales', 'author').get(pk=comment_pk)
        send_new_comment(comment)
    except Comment.DoesNotExist:
        pass


@shared_task
def notify_assigned_to_resolver(ticket_pk):
    from apps.tickets.models import Ticket
    from .email import send_assigned_to_you
    try:
        ticket = Ticket.objects.select_related('resolver').get(pk=ticket_pk)
        if ticket.resolver:
            send_assigned_to_you(ticket, ticket.resolver)
    except Ticket.DoesNotExist:
        pass


@shared_task
def notify_assigned_to_sales(ticket_pk):
    from apps.tickets.models import Ticket
    from .email import send_assigned_to_you
    try:
        ticket = Ticket.objects.select_related('sales').get(pk=ticket_pk)
        if ticket.sales:
            send_assigned_to_you(ticket, ticket.sales)
    except Ticket.DoesNotExist:
        pass


@shared_task
def notify_ticket_closed(ticket_pk, closed_as):
    from apps.tickets.models import Ticket
    from .email import send_ticket_closed
    try:
        ticket = Ticket.objects.select_related('requester').get(pk=ticket_pk)
        send_ticket_closed(ticket, closed_as)
    except Ticket.DoesNotExist:
        pass


@shared_task
def poll_imap_inbox():
    """Celery Beat task — kontroluje doručenou poštu a vytváří tikety."""
    from .imap_polling import process_inbox
    process_inbox()
