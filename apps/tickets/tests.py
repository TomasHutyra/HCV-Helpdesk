"""
Testy viditelnosti tiketů pro uživatele s více rolemi.

Spuštění:
    python manage.py test apps.tickets.tests --settings=helpdesk.settings.local
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import Company, User, UserRole
from apps.tickets.models import Area, Ticket, SavedFilter
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


from apps.tickets.models import TicketWatcher

class TicketWatcherModelTest(TestCase):

    def setUp(self):
        self.co = _company()
        self.area = _area()
        self.requester = _user('req', UserRole.REQUESTER, company=self.co)
        self.ticket = _ticket(self.requester, self.co)

    def test_watcher_created_with_email(self):
        w = TicketWatcher.objects.create(ticket=self.ticket, email='watcher@ext.cz')
        self.assertEqual(w.email, 'watcher@ext.cz')
        self.assertEqual(str(w), 'watcher@ext.cz')

    def test_watcher_with_name_str(self):
        w = TicketWatcher.objects.create(ticket=self.ticket, email='jan@firm.cz', name='Jan Novák')
        self.assertEqual(str(w), 'Jan Novák')

    def test_unique_email_per_ticket(self):
        from django.db import IntegrityError
        TicketWatcher.objects.create(ticket=self.ticket, email='a@b.cz')
        with self.assertRaises(IntegrityError):
            TicketWatcher.objects.create(ticket=self.ticket, email='a@b.cz')

    def test_ticket_watchers_relation(self):
        TicketWatcher.objects.create(ticket=self.ticket, email='x@y.cz')
        self.assertEqual(self.ticket.ticket_watchers.count(), 1)


from apps.tickets.views import _parse_watchers


class ParseWatchersTest(TestCase):

    def test_single_valid_email(self):
        self.assertEqual(_parse_watchers('jan@firma.cz'), {'jan@firma.cz'})

    def test_multiple_emails_comma_separated(self):
        result = _parse_watchers('jan@firma.cz,eva@ext.cz')
        self.assertEqual(result, {'jan@firma.cz', 'eva@ext.cz'})

    def test_whitespace_trimmed(self):
        result = _parse_watchers(' jan@firma.cz , eva@ext.cz ')
        self.assertIn('jan@firma.cz', result)
        self.assertIn('eva@ext.cz', result)

    def test_invalid_email_ignored(self):
        result = _parse_watchers('neni-email, jan@firma.cz')
        self.assertNotIn('neni-email', result)
        self.assertIn('jan@firma.cz', result)

    def test_empty_string_returns_empty_set(self):
        self.assertEqual(_parse_watchers(''), set())

    def test_duplicates_deduplicated(self):
        result = _parse_watchers('jan@firma.cz,jan@firma.cz')
        self.assertEqual(result, {'jan@firma.cz'})

    def test_lowercased(self):
        result = _parse_watchers('JAN@FIRMA.CZ')
        self.assertIn('jan@firma.cz', result)


class SavedFilterModelTest(TestCase):

    def setUp(self):
        self.co = _company()
        self.user = _user('filterer', UserRole.REQUESTER, company=self.co)

    def test_create_saved_filter(self):
        sf = SavedFilter.objects.create(
            user=self.user, name='Moje IT', params={'status': 'open', 'area': '1'},
        )
        self.assertEqual(sf.name, 'Moje IT')
        self.assertEqual(sf.params['status'], 'open')
        self.assertIsNotNone(sf.created_at)

    def test_unique_name_per_user(self):
        from django.db import IntegrityError
        SavedFilter.objects.create(user=self.user, name='Dup', params={})
        with self.assertRaises(IntegrityError):
            SavedFilter.objects.create(user=self.user, name='Dup', params={})

    def test_same_name_different_users(self):
        other = _user('other_f', UserRole.REQUESTER, company=self.co)
        SavedFilter.objects.create(user=self.user, name='Same', params={})
        SavedFilter.objects.create(user=other, name='Same', params={})
        self.assertEqual(SavedFilter.objects.filter(name='Same').count(), 2)

    def test_ordering_by_name(self):
        SavedFilter.objects.create(user=self.user, name='Zebra', params={})
        SavedFilter.objects.create(user=self.user, name='Alfa', params={})
        names = list(SavedFilter.objects.filter(user=self.user).values_list('name', flat=True))
        self.assertEqual(names, ['Alfa', 'Zebra'])

    def test_cascade_delete_user(self):
        SavedFilter.objects.create(user=self.user, name='X', params={})
        self.user.delete()
        self.assertEqual(SavedFilter.objects.count(), 0)


import json


class SavedFilterAPITest(TestCase):

    def setUp(self):
        self.co = _company()
        self.user = _user('api_user', UserRole.REQUESTER, company=self.co)
        self.client.force_login(self.user)

    def test_list_empty(self):
        resp = self.client.get('/tickets/filters/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), [])

    def test_save_creates_filter(self):
        resp = self.client.post(
            '/tickets/filters/save/',
            data=json.dumps({'name': 'Test', 'params': {'status': 'open'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['name'], 'Test')
        self.assertTrue(SavedFilter.objects.filter(user=self.user, name='Test').exists())

    def test_save_upserts_existing(self):
        self.client.post(
            '/tickets/filters/save/',
            data=json.dumps({'name': 'Up', 'params': {'status': 'open'}}),
            content_type='application/json',
        )
        self.client.post(
            '/tickets/filters/save/',
            data=json.dumps({'name': 'Up', 'params': {'status': 'closed'}}),
            content_type='application/json',
        )
        self.assertEqual(SavedFilter.objects.filter(user=self.user, name='Up').count(), 1)
        self.assertEqual(
            SavedFilter.objects.get(user=self.user, name='Up').params['status'], 'closed',
        )

    def test_save_rejects_empty_name(self):
        resp = self.client.post(
            '/tickets/filters/save/',
            data=json.dumps({'name': '', 'params': {}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_own_filter(self):
        sf = SavedFilter.objects.create(user=self.user, name='Del', params={})
        resp = self.client.delete(f'/tickets/filters/{sf.pk}/delete/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(SavedFilter.objects.filter(pk=sf.pk).exists())

    def test_delete_other_users_filter_returns_404(self):
        other = _user('other_api', UserRole.REQUESTER, company=self.co)
        sf = SavedFilter.objects.create(user=other, name='Nope', params={})
        resp = self.client.delete(f'/tickets/filters/{sf.pk}/delete/')
        self.assertEqual(resp.status_code, 404)

    def test_list_returns_own_filters_only(self):
        SavedFilter.objects.create(user=self.user, name='Mine', params={'a': '1'})
        other = _user('other_list', UserRole.REQUESTER, company=self.co)
        SavedFilter.objects.create(user=other, name='Theirs', params={})
        resp = self.client.get('/tickets/filters/')
        data = json.loads(resp.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Mine')

    def test_anonymous_user_redirected(self):
        self.client.logout()
        resp = self.client.get('/tickets/filters/')
        self.assertEqual(resp.status_code, 302)
