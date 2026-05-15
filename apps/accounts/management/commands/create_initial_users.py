from django.core.management.base import BaseCommand

from apps.accounts.models import Company, User, UserRole
from apps.tickets.models import Area

USERS = [
    {
        'first_name': 'Petr',
        'last_name': 'Hutyra',
        'email': 'phutyra@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.MANAGER, UserRole.RESOLVER],
        'company': None,
        'areas': ['Helios'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Martin',
        'last_name': 'Ječmen',
        'email': 'mjecmen@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.MANAGER],
        'company': 'CS Steel',
        'areas': ['IT - koncové stanice', 'IT - servery'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Pavel',
        'last_name': 'Zemánek',
        'email': 'pzemanek@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.MANAGER, UserRole.SALES],
        'company': 'CS Steel',
        'areas': ['Helios'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Lukáš',
        'last_name': 'Hubatka',
        'email': 'lhubatka@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.MANAGER],
        'company': None,
        'areas': ['IT - koncové stanice', 'IT - servery'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Pavel',
        'last_name': 'Preč',
        'email': 'pprec@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.RESOLVER],
        'company': None,
        'areas': ['IT - koncové stanice', 'IT - servery'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Miroslav',
        'last_name': 'Grée',
        'email': 'mgree@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.RESOLVER],
        'company': None,
        'areas': ['IT - koncové stanice', 'IT - servery'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Jaroslav',
        'last_name': 'Ježek',
        'email': 'jjezek@hcv.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.RESOLVER],
        'company': None,
        'areas': ['IT - koncové stanice', 'IT - servery'],
        'language': 'cs',
        'requester_scope': 'own',
    },
    {
        'first_name': 'Aleš',
        'last_name': 'Kárný',
        'email': 'ales.karny@cssteel.cz',
        'password': 'Heslo123!',
        'roles': [UserRole.REQUESTER],
        'company': 'CS Steel',
        'areas': [],
        'language': 'cs',
        'requester_scope': 'company',
    },
]


class Command(BaseCommand):
    help = 'Vytvoří počáteční uživatele dle předpřipravené konfigurace.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skutečně provede vytvoření uživatelů. Bez tohoto přepínače se provede pouze dry-run.',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']

        self.stdout.write('\n=== Uživatelé k vytvoření ===')
        for u in USERS:
            roles_str = ', '.join(u['roles'])
            areas_str = ', '.join(u['areas']) if u['areas'] else '—'
            self.stdout.write(
                f"  {u['first_name']} {u['last_name']} <{u['email']}> "
                f"| role: {roles_str} | firma: {u['company'] or '—'} | oblasti: {areas_str}"
            )

        if not confirm:
            self.stdout.write(
                self.style.WARNING('\nDRY-RUN: nic nebylo vytvořeno. Spusťte s --confirm pro skutečné vytvoření.\n')
            )
            return

        self.stdout.write(self.style.WARNING('\nVytvářím uživatele...'))

        for data in USERS:
            username = data['email'].split('@')[0]

            if User.objects.filter(email=data['email']).exists():
                self.stdout.write(self.style.WARNING(f"  PŘESKOČEN (již existuje): {data['email']}"))
                continue

            # Firma — lookup pro managery a sales = managed_companies; pro requestery = user.company
            company_obj = None
            if data['company']:
                company_obj, _ = Company.objects.get_or_create(name=data['company'])

            # Oblasti
            area_objs = []
            for area_name in data['areas']:
                area_obj, _ = Area.objects.get_or_create(name=area_name)
                area_objs.append(area_obj)

            user = User.objects.create_user(
                username=username,
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                language=data['language'],
                requester_scope=data['requester_scope'],
            )

            # Přiřazení firmy a oblastí dle rolí
            is_requester = UserRole.REQUESTER in data['roles']
            is_manager = UserRole.MANAGER in data['roles']
            is_resolver = UserRole.RESOLVER in data['roles']

            if is_requester and company_obj:
                user.company = company_obj
                user.save()

            if is_manager and company_obj:
                user.managed_companies.add(company_obj)

            if is_manager and area_objs:
                user.managed_areas.set(area_objs)

            if is_resolver and area_objs:
                user.resolver_areas.set(area_objs)

            for role in data['roles']:
                UserRole.objects.create(user=user, role=role)

            roles_str = ', '.join(data['roles'])
            self.stdout.write(self.style.SUCCESS(f"  Vytvořen: {user.get_full_name()} <{user.email}> [{roles_str}]"))

        self.stdout.write(self.style.SUCCESS('\nHotovo.\n'))
