from django.core.management.base import BaseCommand

from apps.accounts.models import Company, User
from apps.tickets.models import Comment, Ticket, TicketAttachment, TicketChange, TimeLog


class Command(BaseCommand):
    help = 'Smaže všechna testovací data (tikety, uživatele kromě superuživatelů, firmy).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skutečně provede smazání. Bez tohoto přepínače se provede pouze dry-run.',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']

        ticket_count = Ticket.objects.count()
        comment_count = Comment.objects.count()
        timelog_count = TimeLog.objects.count()
        change_count = TicketChange.objects.count()
        attachment_count = TicketAttachment.objects.count()
        user_count = User.objects.filter(is_superuser=False).count()
        company_count = Company.objects.count()
        superuser_count = User.objects.filter(is_superuser=True).count()

        self.stdout.write('\n=== Co bude smazáno ===')
        self.stdout.write(f'  Tikety:          {ticket_count}')
        self.stdout.write(f'  Komentáře:       {comment_count}')
        self.stdout.write(f'  Záznamy práce:   {timelog_count}')
        self.stdout.write(f'  Změny tiketu:    {change_count}')
        self.stdout.write(f'  Přílohy:         {attachment_count}')
        self.stdout.write(f'  Uživatelé:       {user_count} (ne-superuživatelé)')
        self.stdout.write(f'  Firmy:           {company_count}')
        self.stdout.write(f'\n=== Co zůstane ===')
        self.stdout.write(f'  Superuživatelé:  {superuser_count}')
        self.stdout.write(f'  Oblasti (Areas) a kategorie práce: beze změny')

        if not confirm:
            self.stdout.write(
                self.style.WARNING('\nDRY-RUN: nic nebylo smazáno. Spusťte s --confirm pro skutečné smazání.\n')
            )
            return

        self.stdout.write(self.style.WARNING('\nMažu data...'))

        # Přílohy — smazat soubory z disku
        deleted_files = 0
        for attachment in TicketAttachment.objects.all():
            try:
                attachment.file.delete(save=False)
                deleted_files += 1
            except Exception:
                pass
        self.stdout.write(f'  Soubory příloh smazány: {deleted_files}/{attachment_count}')

        # Tikety — CASCADE smaže komentáře, záznamy práce, změny, přílohy (záznamy v DB)
        Ticket.objects.all().delete()
        self.stdout.write(f'  Tikety a závislá data smazána.')

        # Uživatelé (ne-superuživatelé) — CASCADE smaže UserRole
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(f'  Uživatelé smazáni.')

        # Firmy
        Company.objects.all().delete()
        self.stdout.write(f'  Firmy smazány.')

        self.stdout.write(self.style.SUCCESS('\nHotovo. Databáze je připravena pro ostré spuštění.\n'))
