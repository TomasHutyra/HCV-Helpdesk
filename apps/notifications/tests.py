"""
Testy pro notifikace — fokus na _get_notifiable_resolvers().

Spuštění:
    python manage.py test apps.notifications.tests --settings=helpdesk.settings.local
"""
from django.test import TestCase

from apps.accounts.models import Company, User, UserRole
from apps.notifications.email import _get_notifiable_resolvers
from apps.tickets.models import Area, Ticket


def _make_company():
    return Company.objects.create(name='Testovací firma')


def _make_requester(company):
    u = User.objects.create_user(
        username='requester', email='requester@test.cz', password='x'
    )
    u.company = company
    u.save()
    UserRole.objects.create(user=u, role=UserRole.REQUESTER)
    return u


def _make_resolver(username, email, notify=False, areas=None, active=True):
    """Vytvoří řešitele s volitelným notify_new_ticket a oblastmi."""
    u = User.objects.create_user(
        username=username, email=email, password='x', is_active=active
    )
    u.notify_new_ticket = notify
    u.save()
    UserRole.objects.create(user=u, role=UserRole.RESOLVER)
    if areas:
        u.resolver_areas.set(areas)
    return u


def _make_ticket(requester, company, area=None):
    return Ticket.objects.create(
        type=Ticket.TYPE_PROBLEM,
        title='Testovací tiket',
        description='Popis',
        area=area,
        priority=Ticket.PRIORITY_MEDIUM,
        company=company,
        requester=requester,
    )


class GetNotifiableResolversTest(TestCase):

    def setUp(self):
        self.company = _make_company()
        self.requester = _make_requester(self.company)
        self.area_it = Area.objects.create(name='IT')
        self.area_helios = Area.objects.create(name='Helios')
        self.area_unknown = Area.objects.create(name='Neznámá', is_unknown=True)

    # ------------------------------------------------------------------
    # notify_new_ticket = False → vždy NE
    # ------------------------------------------------------------------

    def test_resolver_notify_off_is_excluded(self):
        """Řešitel s vypnutou notifikací nedostane e-mail bez ohledu na oblast."""
        _make_resolver('r1', 'r1@test.cz', notify=False, areas=[self.area_it])
        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        self.assertNotIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    # ------------------------------------------------------------------
    # Žádné oblasti řešitele → sleduje vše
    # ------------------------------------------------------------------

    def test_no_areas_notified_for_it_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[])
        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_no_areas_notified_for_helios_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[])
        ticket = _make_ticket(self.requester, self.company, area=self.area_helios)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_no_areas_notified_for_unknown_area_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[])
        ticket = _make_ticket(self.requester, self.company, area=self.area_unknown)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_no_areas_notified_for_null_area_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[])
        ticket = _make_ticket(self.requester, self.company, area=None)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    # ------------------------------------------------------------------
    # Řešitel má přiřazenu oblast [IT]
    # ------------------------------------------------------------------

    def test_it_resolver_notified_for_it_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_it])
        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_it_resolver_excluded_for_helios_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_it])
        ticket = _make_ticket(self.requester, self.company, area=self.area_helios)
        self.assertNotIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_it_resolver_notified_for_unknown_area_ticket(self):
        """Varianta B: Neznámá oblast → notifikace všem aktivním řešitelům."""
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_it])
        ticket = _make_ticket(self.requester, self.company, area=self.area_unknown)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_it_resolver_notified_for_null_area_ticket(self):
        """Varianta B: null oblast → notifikace všem aktivním řešitelům."""
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_it])
        ticket = _make_ticket(self.requester, self.company, area=None)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    # ------------------------------------------------------------------
    # Řešitel má přiřazenu oblast [Helios]
    # ------------------------------------------------------------------

    def test_helios_resolver_excluded_for_it_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_helios])
        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        self.assertNotIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_helios_resolver_notified_for_helios_ticket(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_helios])
        ticket = _make_ticket(self.requester, self.company, area=self.area_helios)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    def test_helios_resolver_notified_for_unknown_area_ticket(self):
        """Varianta B: Neznámá oblast → notifikace i řešitelům jiné oblasti."""
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[self.area_helios])
        ticket = _make_ticket(self.requester, self.company, area=self.area_unknown)
        self.assertIn('r1@test.cz', _get_notifiable_resolvers(ticket))

    # ------------------------------------------------------------------
    # Více řešitelů naráz
    # ------------------------------------------------------------------

    def test_multiple_resolvers_only_matching_notified(self):
        r_it = _make_resolver('r_it', 'r_it@test.cz', notify=True, areas=[self.area_it])
        r_helios = _make_resolver('r_helios', 'r_helios@test.cz', notify=True, areas=[self.area_helios])
        r_all = _make_resolver('r_all', 'r_all@test.cz', notify=True, areas=[])
        r_off = _make_resolver('r_off', 'r_off@test.cz', notify=False, areas=[self.area_it])

        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        result = _get_notifiable_resolvers(ticket)

        self.assertIn('r_it@test.cz', result)
        self.assertNotIn('r_helios@test.cz', result)
        self.assertIn('r_all@test.cz', result)
        self.assertNotIn('r_off@test.cz', result)

    # ------------------------------------------------------------------
    # Neaktivní řešitel
    # ------------------------------------------------------------------

    def test_inactive_resolver_excluded(self):
        _make_resolver('r1', 'r1@test.cz', notify=True, areas=[], active=False)
        ticket = _make_ticket(self.requester, self.company, area=self.area_it)
        self.assertNotIn('r1@test.cz', _get_notifiable_resolvers(ticket))
