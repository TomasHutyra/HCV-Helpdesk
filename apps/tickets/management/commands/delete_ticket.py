from django.core.management.base import BaseCommand, CommandError

from apps.tickets.models import Ticket


class Command(BaseCommand):
    help = 'Smaže konkrétní tiket včetně všech navázaných dat.'

    def add_arguments(self, parser):
        parser.add_argument('ticket_id', type=int, help='ID tiketu ke smazání')
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skutečně provede smazání. Bez tohoto přepínače se provede pouze dry-run.',
        )

    def handle(self, *args, **options):
        pk = options['ticket_id']
        confirm = options['confirm']

        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            raise CommandError(f'Tiket #{pk} neexistuje.')

        comments = ticket.comments.count()
        time_logs = ticket.time_logs.count()
        attachments = ticket.attachments.count()
        history = ticket.history.count()
        watchers = ticket.ticket_watchers.count()

        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'Tiket #{ticket.pk}: {ticket.title}'))
        self.stdout.write(f'  Stav:       {ticket.get_status_display()}')
        self.stdout.write(f'  Typ:        {ticket.get_type_display()}')
        self.stdout.write(f'  Firma:      {ticket.company}')
        self.stdout.write(f'  Žadatel:    {ticket.requester}')
        self.stdout.write(f'  Vytvořeno:  {ticket.created_at:%d.%m.%Y %H:%M}')
        self.stdout.write('')
        self.stdout.write('Bude smazáno:')
        self.stdout.write(f'  {comments} komentář(ů)')
        self.stdout.write(f'  {time_logs} záznam(ů) času')
        self.stdout.write(f'  {attachments} příloha(h)')
        self.stdout.write(f'  {history} záznam(ů) historie')
        self.stdout.write(f'  {watchers} sledující(ch)')
        self.stdout.write('')

        if not confirm:
            self.stdout.write(self.style.NOTICE(
                'Dry-run — spusťte s --confirm pro skutečné smazání.'
            ))
            return

        ticket.delete()
        self.stdout.write(self.style.SUCCESS(f'Tiket #{pk} byl smazán.'))
