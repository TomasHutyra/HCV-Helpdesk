"""
Testy viditelnosti tiketů pro uživatele s více rolemi.

Spuštění:
    python manage.py test apps.tickets.tests --settings=helpdesk.settings.local
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import Company, User, UserRole
from apps.tickets.models import Area, Ticket
from apps.tickets.views import _build_user_ticket_q, _can_comment, _can_add_attachment


def _company():
    return Company.objects.create(name='Firma')


def _area(name='IT'):
    return Area.objects.create(name=name)


def _user(username, *roles, company=None, resolver_areas=None):
    u = User.objects.create_user(username=username, email=f'{username}@t.cz', password='x')
    if company:
        u.company = company
        u.save()
    for role in roles:
        UserRole.objects.create(user=u, role=role)
    if resolver_areas is not None:
        u.resolver_areas.set(resolver_areas)
    return u


def _ticket(requester, company, area=None, resolver=None):
    t = Ticket.objects.create(
        type=Ticket.TYPE_PROBLEM,
        title='T', description='D',
        area=area, priority=Ticket.PRIORITY_MEDIUM,
        company=company, requester=requester,
    )
    if resolver:
        # Queryset update + nová instance (refresh_from_db selže kvůli FSM ochraně pk instance)
        Ticket.objects.filter(pk=t.pk).update(
            resolver=resolver, status=Ticket.STATUS_IN_PROGRESS
        )
        return Ticket.objects.get(pk=t.pk)
    return t


class MultiRoleVisibilityTest(TestCase):
    """Uživatel s rolemi řešitel+žadatel musí vidět tikety z obou rolí."""

    def setUp(self):
        self.co = _company()
        self.area_it = _area('IT')
        self.area_helios = _area('Helios')
        # Druhý žadatel pro tikety, které nejsou naše
        self.other_requester = _user('other', UserRole.REQUESTER, company=self.co)

    def _visible_ids(self, user):
        q = _build_user_ticket_q(user)
        if q is None:
            return set()
        return set(Ticket.objects.filter(q).values_list('pk', flat=True))

    # ------------------------------------------------------------------
    # Pouze řešitel (sanity check — stávající chování se nesmí změnit)
    # ------------------------------------------------------------------

    def test_pure_resolver_sees_assigned_and_new_in_area(self):
        resolver = _user('r', UserRole.RESOLVER, resolver_areas=[self.area_it])
        assigned = _ticket(self.other_requester, self.co, area=self.area_it, resolver=resolver)
        new_it = _ticket(self.other_requester, self.co, area=self.area_it)
        new_helios = _ticket(self.other_requester, self.co, area=self.area_helios)

        visible = self._visible_ids(resolver)
        self.assertIn(assigned.pk, visible)
        self.assertIn(new_it.pk, visible)
        self.assertNotIn(new_helios.pk, visible)

    # ------------------------------------------------------------------
    # Pouze žadatel (sanity check)
    # ------------------------------------------------------------------

    def test_pure_requester_sees_own_tickets_only(self):
        requester = _user('req', UserRole.REQUESTER, company=self.co)
        own = _ticket(requester, self.co, area=self.area_it)
        other = _ticket(self.other_requester, self.co, area=self.area_it)

        visible = self._visible_ids(requester)
        self.assertIn(own.pk, visible)
        self.assertNotIn(other.pk, visible)

    # ------------------------------------------------------------------
    # Řešitel + žadatel — hlavní test
    # ------------------------------------------------------------------

    def test_resolver_requester_sees_own_created_tickets(self):
        """Uživatel s oběma rolemi musí vidět tikety, které sám zadal."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER,
                     company=self.co, resolver_areas=[self.area_it])
        own_ticket = _ticket(dual, self.co, area=self.area_helios)  # oblast mimo jeho řešitelskou

        visible = self._visible_ids(dual)
        self.assertIn(own_ticket.pk, visible)

    def test_resolver_requester_sees_assigned_tickets(self):
        """Uživatel s oběma rolemi musí vidět tikety, které mu jsou přiřazeny."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER,
                     company=self.co, resolver_areas=[self.area_it])
        assigned = _ticket(self.other_requester, self.co, area=self.area_it, resolver=dual)

        visible = self._visible_ids(dual)
        self.assertIn(assigned.pk, visible)

    def test_resolver_requester_sees_new_in_area(self):
        """Uživatel s oběma rolemi musí vidět nové tikety v jeho oblastech."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER,
                     company=self.co, resolver_areas=[self.area_it])
        new_it = _ticket(self.other_requester, self.co, area=self.area_it)

        visible = self._visible_ids(dual)
        self.assertIn(new_it.pk, visible)

    def test_resolver_requester_does_not_see_unrelated_tickets(self):
        """Uživatel s oběma rolemi nesmí vidět cizí tikety mimo jeho oblasti."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER,
                     company=self.co, resolver_areas=[self.area_it])
        unrelated = _ticket(self.other_requester, self.co, area=self.area_helios)

        visible = self._visible_ids(dual)
        self.assertNotIn(unrelated.pk, visible)

    def test_resolver_requester_all_three_categories_at_once(self):
        """Kombinovaný test: vidí vlastní + přiřazené + nové v oblasti."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER,
                     company=self.co, resolver_areas=[self.area_it])

        own = _ticket(dual, self.co, area=self.area_helios)           # vlastní, mimo oblast
        assigned = _ticket(self.other_requester, self.co, area=self.area_helios, resolver=dual)  # přiřazený
        new_it = _ticket(self.other_requester, self.co, area=self.area_it)   # nový v oblasti
        unrelated = _ticket(self.other_requester, self.co, area=self.area_helios)  # cizí, bez řešitele

        visible = self._visible_ids(dual)
        self.assertIn(own.pk, visible)
        self.assertIn(assigned.pk, visible)
        self.assertIn(new_it.pk, visible)
        self.assertNotIn(unrelated.pk, visible)


class MultiRoleCommentTest(TestCase):
    """Uživatel resolver+requester musí mít právo komentovat vlastní tiket."""

    def setUp(self):
        self.co = _company()
        self.area = _area()

    def test_resolver_requester_can_comment_own_ticket_without_being_assigned(self):
        """Pokud je uživatel žadatel tiketu, může komentovat i když není přiřazený řešitel."""
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER, company=self.co)
        ticket = _ticket(dual, self.co, area=self.area)  # dual je žadatel, není přiřazen jako řešitel

        self.assertTrue(_can_comment(dual, ticket))

    def test_resolver_requester_can_add_attachment_to_own_ticket(self):
        dual = _user('dual', UserRole.RESOLVER, UserRole.REQUESTER, company=self.co)
        ticket = _ticket(dual, self.co, area=self.area)

        self.assertTrue(_can_add_attachment(dual, ticket))
