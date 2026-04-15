from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ručně spustí IMAP polling a vytvoří tikety z nepřečtených e-mailů.'

    def handle(self, *args, **options):
        from apps.notifications.imap_polling import process_inbox
        self.stdout.write('Spouštím IMAP polling…')
        process_inbox()
        self.stdout.write(self.style.SUCCESS('Hotovo.'))
