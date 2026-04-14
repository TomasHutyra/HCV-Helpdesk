"""
Přiřadí role uživateli z příkazové řádky.

Použití:
    python manage.py assign_roles thutyra admin manager
    python manage.py assign_roles jnovak resolver
    python manage.py assign_roles --list         # vypíše všechny uživatele a jejich role
"""
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import User, UserRole


class Command(BaseCommand):
    help = 'Přiřadí aplikační role uživateli'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?', help='Uživatelské jméno')
        parser.add_argument(
            'roles', nargs='*',
            choices=[r for r, _ in UserRole.ROLE_CHOICES],
            help='Role: admin manager resolver sales requester',
        )
        parser.add_argument('--list', action='store_true', help='Zobrazit uživatele a jejich role')

    def handle(self, *args, **options):
        if options['list']:
            self._list_users()
            return

        username = options.get('username')
        roles = options.get('roles', [])

        if not username:
            raise CommandError('Zadejte uživatelské jméno.')
        if not roles:
            raise CommandError('Zadejte alespoň jednu roli.')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Uživatel "{username}" neexistuje.')

        added = []
        for role in roles:
            _, created = UserRole.objects.get_or_create(user=user, role=role)
            if created:
                added.append(role)

        current = list(user.user_roles.values_list('role', flat=True))
        self.stdout.write(self.style.SUCCESS(
            f'Uživatel {username}: role přiřazeny {added or "(již existovaly)"}. '
            f'Aktuální role: {current}'
        ))

    def _list_users(self):
        self.stdout.write(f'{"Uživatel":<20} {"Role"}')
        self.stdout.write('-' * 50)
        for user in User.objects.prefetch_related('user_roles').order_by('username'):
            roles = ', '.join(user.user_roles.values_list('role', flat=True)) or '—'
            self.stdout.write(f'{user.username:<20} {roles}')
