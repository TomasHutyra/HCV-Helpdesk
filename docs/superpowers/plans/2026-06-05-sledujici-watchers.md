# Sledující (Watchers) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přidat model `TicketWatcher` a umožnit přidávání/odebírání sledujících (uživatelů nebo externích e-mailů) při zakládání a editaci tiketu; sledující dostávají všechny notifikace o tiketu.

**Architecture:** `TicketWatcher` je samostatný model s FK na Ticket a polem `email` (unikátní per tiket). Pole `watchers` se zpracovává mimo ModelForm — čte se přímo z `request.POST` a synchronizuje se v `form_valid()`. Notifikační funkce v `email.py` dostávají sledující přes helper `_get_watcher_emails()` a přidávají je do existujících příjemců.

**Tech Stack:** Django 4.x, django-fsm, Celery (eager v testech), vanilla JS (chips widget), SQLite (dev) / PostgreSQL (prod)

---

## Dotčené soubory

| Akce | Soubor |
|---|---|
| Vytvoří (auto) | `apps/tickets/migrations/0014_ticketwatcher.py` |
| Upraví | `apps/tickets/models.py` |
| Upraví | `apps/tickets/views.py` |
| Upraví | `apps/notifications/email.py` |
| Upraví | `templates/tickets/ticket_form.html` |
| Upraví | `templates/tickets/ticket_detail.html` |
| Upraví | `apps/tickets/tests.py` |
| Upraví | `apps/notifications/tests.py` |

---

## Task 1: Model TicketWatcher + migrace

**Files:**
- Modify: `apps/tickets/models.py` (konec souboru, za `TicketAttachment`)
- Create: `apps/tickets/migrations/0014_ticketwatcher.py` (auto)

- [ ] **Krok 1: Napsat failing test pro model**

Přidej na konec `apps/tickets/tests.py`:

```python
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
```

- [ ] **Krok 2: Spustit test — očekávej FAIL (ImportError nebo AttributeError)**

```
python manage.py test apps.tickets.tests.TicketWatcherModelTest --settings=helpdesk.settings.local
```

Očekávané: `ImportError: cannot import name 'TicketWatcher'`

- [ ] **Krok 3: Přidat TicketWatcher do models.py**

Na konec `apps/tickets/models.py` přidej:

```python
class TicketWatcher(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='ticket_watchers', verbose_name=_('tiket'),
    )
    email = models.EmailField(_('e-mail'))
    name = models.CharField(_('jméno'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('sledující')
        verbose_name_plural = _('sledující')
        unique_together = [('ticket', 'email')]
        ordering = ['name', 'email']

    def __str__(self):
        return self.name or self.email
```

- [ ] **Krok 4: Vytvořit migraci**

```
python manage.py makemigrations tickets --name ticketwatcher --settings=helpdesk.settings.local
```

Očekávané: `Migrations for 'tickets': apps/tickets/migrations/0014_ticketwatcher.py`

- [ ] **Krok 5: Aplikovat migraci**

```
python manage.py migrate --settings=helpdesk.settings.local
```

- [ ] **Krok 6: Spustit test — očekávej PASS**

```
python manage.py test apps.tickets.tests.TicketWatcherModelTest --settings=helpdesk.settings.local
```

- [ ] **Krok 7: Commit**

```
git add apps/tickets/models.py apps/tickets/migrations/0014_ticketwatcher.py apps/tickets/tests.py
git commit -m "feat: model TicketWatcher — sledující tiket"
```

---

## Task 2: Notifikace — rozšíření příjemců o sledující

**Files:**
- Modify: `apps/notifications/email.py`
- Modify: `apps/notifications/tests.py`

- [ ] **Krok 1: Napsat failing testy pro notifikace sledujících**

Přidej na konec `apps/notifications/tests.py`:

```python
from django.test import TestCase, override_settings
from apps.notifications.email import (
    _get_watcher_emails, send_new_ticket, send_status_change,
    send_new_comment, send_ticket_closed,
)
from apps.tickets.models import Comment, TicketWatcher


def _make_manager():
    u = User.objects.create_user(username='mgr', email='mgr@test.cz', password='x')
    UserRole.objects.create(user=u, role=UserRole.MANAGER)
    return u


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='http://localhost:8000',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class WatcherNotificationTest(TestCase):

    def setUp(self):
        from django.core import mail
        mail.outbox = []
        self.company = _make_company()
        self.requester = _make_requester(self.company)
        self.ticket = _make_ticket(self.requester, self.company)
        TicketWatcher.objects.create(ticket=self.ticket, email='watcher@ext.cz', name='Watcher')

    def test_get_watcher_emails_returns_list(self):
        emails = _get_watcher_emails(self.ticket)
        self.assertIn('watcher@ext.cz', emails)

    def test_get_watcher_emails_empty_when_none(self):
        self.ticket.ticket_watchers.all().delete()
        self.assertEqual(_get_watcher_emails(self.ticket), [])

    def test_send_new_ticket_includes_watcher(self):
        from django.core import mail
        send_new_ticket(self.ticket)
        all_recipients = []
        for m in mail.outbox:
            all_recipients += m.to + m.cc
        self.assertIn('watcher@ext.cz', all_recipients)

    def test_send_status_change_includes_watcher(self):
        from django.core import mail
        send_status_change(self.ticket)
        all_recipients = []
        for m in mail.outbox:
            all_recipients += m.to + m.cc
        self.assertIn('watcher@ext.cz', all_recipients)

    def test_send_ticket_closed_includes_watcher(self):
        from django.core import mail
        send_ticket_closed(self.ticket, 'resolved')
        all_recipients = []
        for m in mail.outbox:
            all_recipients += m.to + m.cc
        self.assertIn('watcher@ext.cz', all_recipients)

    def test_send_new_comment_includes_watcher(self):
        from django.core import mail
        author = _make_resolver('author', 'author@test.cz', notify=False)
        comment = Comment.objects.create(ticket=self.ticket, author=author, body='Ahoj')
        send_new_comment(comment)
        all_recipients = []
        for m in mail.outbox:
            all_recipients += m.to + m.cc
        self.assertIn('watcher@ext.cz', all_recipients)

    def test_watcher_excluded_from_comment_if_author(self):
        """Sledující, který napsal komentář, nedostane e-mail sám sobě."""
        from django.core import mail
        author = User.objects.create_user(username='wauth', email='watcher@ext.cz', password='x')
        comment = Comment.objects.create(ticket=self.ticket, author=author, body='Píšu já')
        send_new_comment(comment)
        all_recipients = []
        for m in mail.outbox:
            all_recipients += m.to + m.cc
        self.assertNotIn('watcher@ext.cz', all_recipients)
```

- [ ] **Krok 2: Spustit testy — očekávej FAIL**

```
python manage.py test apps.notifications.tests.WatcherNotificationTest --settings=helpdesk.settings.local
```

Očekávané: `AttributeError: module 'apps.notifications.email' has no attribute '_get_watcher_emails'`

- [ ] **Krok 3: Přidat helper a upravit send funkce v email.py**

V `apps/notifications/email.py` přidej **za `_cc_emails`**:

```python
def _get_watcher_emails(ticket):
    """Vrátí seznam e-mailů sledujících tiketu."""
    return list(ticket.ticket_watchers.values_list('email', flat=True))
```

Uprav `send_new_ticket` — přidej sledující do recipients:

```python
def send_new_ticket(ticket):
    """Nový tiket → žadateli + oprávněným správcům + přihlášeným řešitelům + sledujícím."""
    managers = _get_notifiable_managers(ticket)
    resolvers = _get_notifiable_resolvers(ticket)
    watchers = _get_watcher_emails(ticket)
    recipients = list({ticket.requester.email} | set(managers) | set(resolvers) | set(watchers))
    recipients_set = set(recipients)

    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový tiket #{ticket.pk}: {ticket.title}'),
        template='emails/new_ticket.txt',
        context={'ticket': ticket},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients_set],
    )
```

Uprav `send_status_change`:

```python
def send_status_change(ticket):
    """Změna stavu na Řeší se nebo Příprava nabídky → žadateli + sledujícím."""
    recipients_set = {ticket.requester.email}
    recipients_set.update(_get_watcher_emails(ticket))
    recipients = list(recipients_set)
    _send(
        subject=f'[HCV Helpdesk] Stav tiketu #{ticket.pk} změněn: {ticket.get_status_display()}',
        template='emails/status_change.txt',
        context={'ticket': ticket},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients_set],
    )
```

Uprav `send_new_comment`:

```python
def send_new_comment(comment):
    """Nový komentář → všem přiřazeným osobám + sledujícím (kromě autora komentáře)."""
    ticket = comment.ticket
    recipients_set = {ticket.requester.email}
    if ticket.resolver:
        recipients_set.add(ticket.resolver.email)
    if ticket.sales:
        recipients_set.add(ticket.sales.email)
    recipients_set.update(_get_watcher_emails(ticket))
    recipients_set.discard(comment.author.email)

    cc = [e for e in _cc_emails(ticket) if e not in recipients_set and e != comment.author.email]
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Nový komentář k tiketu #{ticket.pk}: {ticket.title}'),
        template='emails/new_comment.txt',
        context={'ticket': ticket, 'comment': comment},
        recipients=list(recipients_set),
        ticket_id=ticket.pk,
        cc=cc,
    )
```

Uprav `send_ticket_closed`:

```python
def send_ticket_closed(ticket, closed_as):
    """Vyřešení nebo zamítnutí → žadateli + sledujícím."""
    recipients_set = {ticket.requester.email}
    recipients_set.update(_get_watcher_emails(ticket))
    recipients = list(recipients_set)
    _send(
        subject=_sanitize_subject(f'[HCV Helpdesk] Tiket #{ticket.pk} {ticket.get_status_display()}: {ticket.title}'),
        template='emails/ticket_closed.txt',
        context={'ticket': ticket, 'closed_as': closed_as},
        recipients=recipients,
        ticket_id=ticket.pk,
        cc=[e for e in _cc_emails(ticket) if e not in recipients_set],
    )
    if closed_as == 'resolved':
        send_rating_request(ticket)
```

- [ ] **Krok 4: Spustit testy — očekávej PASS**

```
python manage.py test apps.notifications.tests.WatcherNotificationTest --settings=helpdesk.settings.local
```

- [ ] **Krok 5: Spustit všechny testy — nesmí být regrese**

```
python manage.py test --settings=helpdesk.settings.local
```

- [ ] **Krok 6: Commit**

```
git add apps/notifications/email.py apps/notifications/tests.py
git commit -m "feat: notifikace — sledující dostávají e-maily o tiketu"
```

---

## Task 3: View — zpracování pole watchers

**Files:**
- Modify: `apps/tickets/views.py`
- Modify: `apps/tickets/tests.py`

- [ ] **Krok 1: Napsat failing test pro _parse_watchers**

Přidej do `apps/tickets/tests.py` (za `TicketWatcherModelTest`):

```python
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
```

- [ ] **Krok 2: Spustit test — očekávej FAIL**

```
python manage.py test apps.tickets.tests.ParseWatchersTest --settings=helpdesk.settings.local
```

Očekávané: `ImportError: cannot import name '_parse_watchers'`

- [ ] **Krok 3: Přidat _parse_watchers do views.py**

V `apps/tickets/views.py` přidej **za funkci `_validate_upload`** (cca řádek 52):

```python
def _parse_watchers(raw):
    """Parsuje comma-separated e-maily. Vrátí set platných lower-case e-mailů."""
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    emails = set()
    for part in raw.split(','):
        email = part.strip().lower()
        if email:
            try:
                validate_email(email)
                emails.add(email)
            except ValidationError:
                pass
    return emails
```

- [ ] **Krok 4: Spustit test — očekávej PASS**

```
python manage.py test apps.tickets.tests.ParseWatchersTest --settings=helpdesk.settings.local
```

- [ ] **Krok 5: Aktualizovat TicketCreateView**

V `apps/tickets/views.py` v `TicketCreateView` přidej metodu `get_context_data` **před** `form_valid`:

```python
def get_context_data(self, **kwargs):
    from apps.accounts.models import User as AccountUser
    ctx = super().get_context_data(**kwargs)
    ctx['show_watchers_field'] = True
    ctx['initial_watchers'] = ''
    ctx['watcher_user_options'] = AccountUser.objects.filter(
        is_active=True
    ).order_by('last_name', 'first_name')
    return ctx
```

Na konci `TicketCreateView.form_valid()`, **před** `notify_new_ticket.delay(ticket.pk)`, přidej:

```python
# Sledující
from apps.accounts.models import User as AccountUser
from .models import TicketWatcher
raw_watchers = self.request.POST.get('watchers', '')
for email in _parse_watchers(raw_watchers):
    user_match = AccountUser.objects.filter(email__iexact=email).first()
    TicketWatcher.objects.get_or_create(
        ticket=ticket, email=email,
        defaults={'name': user_match.get_full_name() if user_match else ''},
    )
```

- [ ] **Krok 6: Aktualizovat TicketUpdateView**

V `apps/tickets/views.py` v `TicketUpdateView` přidej metodu `get_context_data` **před** `dispatch`:

```python
def get_context_data(self, **kwargs):
    from apps.accounts.models import User as AccountUser
    ctx = super().get_context_data(**kwargs)
    ctx['show_watchers_field'] = True
    existing = ','.join(
        self.object.ticket_watchers.values_list('email', flat=True)
    )
    ctx['initial_watchers'] = existing
    ctx['watcher_user_options'] = AccountUser.objects.filter(
        is_active=True
    ).order_by('last_name', 'first_name')
    return ctx
```

Na konci `TicketUpdateView.form_valid()`, **před** `messages.success(...)`, přidej:

```python
# Sledující — sync
from apps.accounts.models import User as AccountUser
from .models import TicketWatcher
raw_watchers = self.request.POST.get('watchers', '')
new_emails = _parse_watchers(raw_watchers)
ticket.ticket_watchers.exclude(email__in=new_emails).delete()
for email in new_emails:
    if not ticket.ticket_watchers.filter(email=email).exists():
        user_match = AccountUser.objects.filter(email__iexact=email).first()
        TicketWatcher.objects.create(
            ticket=ticket, email=email,
            name=user_match.get_full_name() if user_match else '',
        )
```

- [ ] **Krok 7: Přidat sledující do kontextu TicketDetailView**

V `TicketDetailView.get_context_data()`, na konec (před `return ctx`):

```python
ctx['watchers'] = ticket.ticket_watchers.all()
```

- [ ] **Krok 8: Spustit všechny testy — nesmí být regrese**

```
python manage.py test --settings=helpdesk.settings.local
```

- [ ] **Krok 9: Commit**

```
git add apps/tickets/views.py apps/tickets/tests.py
git commit -m "feat: views — ukládání a sync sledujících při create/update tiketu"
```

---

## Task 4: Šablona ticket_form.html — widget sledujících

**Files:**
- Modify: `templates/tickets/ticket_form.html`

- [ ] **Krok 1: Přidat widget sledujících do formuláře**

V `templates/tickets/ticket_form.html` přidej **za sekci Kontaktní osoba** (za uzavírací `</div>` sekce kontaktní osoby, před sekci Přílohy na řádku `{% if not object %}`):

```html
{% if show_watchers_field %}
<div style="margin-top:8px;padding-top:16px;border-top:1px solid var(--c-border)">
  <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--c-text-muted);margin-bottom:10px">
    {% trans "Sledující" %} <span style="font-weight:400;text-transform:none;letter-spacing:0">({% trans "volitelné" %})</span>
  </div>
  <div style="display:flex;gap:8px;margin-bottom:8px">
    <input type="text" id="watcher-input" list="watcher-datalist"
           placeholder="{% trans 'e-mail nebo jméno...' %}"
           style="flex:1;min-width:0">
    <datalist id="watcher-datalist">
      {% for u in watcher_user_options %}
      <option value="{{ u.email }}">{{ u.get_full_name }} ({{ u.email }})</option>
      {% endfor %}
    </datalist>
    <button type="button" class="btn btn-secondary" onclick="watcherAdd()">+ {% trans "Přidat" %}</button>
  </div>
  <div id="watcher-chips" style="display:flex;flex-wrap:wrap;gap:6px;min-height:4px"></div>
  <input type="hidden" name="watchers" id="watchers-hidden" value="{{ initial_watchers }}">
</div>

<script>
(function () {
  var hidden = document.getElementById('watchers-hidden');
  var chips = document.getElementById('watcher-chips');
  var input = document.getElementById('watcher-input');

  function getEmails() {
    var val = hidden.value.trim();
    return val ? val.split(',').map(function(e){ return e.trim(); }).filter(Boolean) : [];
  }

  function setEmails(arr) {
    hidden.value = arr.join(',');
  }

  function renderChips() {
    chips.innerHTML = '';
    getEmails().forEach(function(email) {
      var chip = document.createElement('span');
      chip.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:3px 10px;background:var(--c-bg);border:1px solid var(--c-border);border-radius:999px;font-size:13px';
      var label = document.createElement('span');
      label.textContent = email;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = '×';
      btn.style.cssText = 'background:none;border:none;cursor:pointer;padding:0;line-height:1;color:var(--c-text-muted);font-size:16px';
      btn.setAttribute('data-email', email);
      btn.addEventListener('click', function() {
        setEmails(getEmails().filter(function(e){ return e !== this.getAttribute('data-email'); }.bind(this)));
        renderChips();
      });
      chip.appendChild(label);
      chip.appendChild(btn);
      chips.appendChild(chip);
    });
  }

  window.watcherAdd = function() {
    var val = input.value.trim().toLowerCase();
    if (!val || val.indexOf('@') === -1) return;
    var emails = getEmails();
    if (emails.indexOf(val) === -1) {
      emails.push(val);
      setEmails(emails);
      renderChips();
    }
    input.value = '';
    input.focus();
  };

  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); watcherAdd(); }
  });

  renderChips();
}());
</script>
{% endif %}
```

- [ ] **Krok 2: Vizuálně ověřit formulář v prohlížeči**

```
python manage.py runserver --settings=helpdesk.settings.local
```

Ověř:
- Přejdi na `/tickets/new/` — sekce Sledující se zobrazí pod Kontaktní osobou.
- Zadej e-mail do pole a klikni "+ Přidat" — chip se zobrazí.
- Klikni Enter v poli — chip se přidá.
- Klikni `×` na chipu — chip zmizí.
- Odešli formulář — tiket se vytvoří, sledující se uloží (ověř přes Django admin nebo shell).
- Přejdi na editaci tiketu — existující sledující jsou předvyplněni jako chipy.

- [ ] **Krok 3: Commit**

```
git add templates/tickets/ticket_form.html
git commit -m "feat: formulář tiketů — widget pro přidávání sledujících"
```

---

## Task 5: Šablona ticket_detail.html — zobrazení sledujících

**Files:**
- Modify: `templates/tickets/ticket_detail.html`

- [ ] **Krok 1: Přidat sledující do postranního sloupce**

V `templates/tickets/ticket_detail.html` v sekci `{# Metadata #}` (uvnitř `.card.card-body-sm`), přidej **za blok Kontaktní osoba** (za uzavírací `{% endif %}` kontaktní osoby, před meta-row Řešitel):

```html
{% if watchers %}
<div class="meta-row" style="align-items:flex-start">
  <span class="meta-label">{% trans "Sledující" %}</span>
  <span class="meta-value" style="font-weight:400">
    {% for w in watchers %}
    <span style="display:block;font-size:13px">
      {% if w.name %}{{ w.name }} <span style="color:var(--c-text-muted)">({{ w.email }})</span>{% else %}{{ w.email }}{% endif %}
    </span>
    {% endfor %}
  </span>
</div>
{% endif %}
```

- [ ] **Krok 2: Vizuálně ověřit detail tiketu**

```
python manage.py runserver --settings=helpdesk.settings.local
```

Ověř:
- Detail tiketu se sledujícím zobrazí sekci „Sledující" v postranním sloupci.
- Detail tiketu bez sledujících sekci nezobrazí.
- Sledující s jménem: zobrazí se „Jan Novák (jan@firma.cz)".
- Sledující bez jména: zobrazí se jen „eva@ext.cz".

- [ ] **Krok 3: Commit**

```
git add templates/tickets/ticket_detail.html
git commit -m "feat: detail tiketu — zobrazení sledujících v postranním sloupci"
```

---

## Task 6: Finální ověření — end-to-end a všechny testy

- [ ] **Krok 1: Spustit celou testovací sadu**

```
python manage.py test --settings=helpdesk.settings.local
```

Očekávané: všechny testy PASS, žádné chyby.

- [ ] **Krok 2: Manuální end-to-end ověření**

```
python manage.py runserver --settings=helpdesk.settings.local
```

Scénář 1 — přidání sledujícího při zakládání:
1. Založ nový tiket, přidej sledujícího `test@ext.cz`.
2. Ověř v Django admin (`/admin/tickets/ticketwatcher/`), že záznam vznikl.

Scénář 2 — editace sledujících:
1. Přejdi na editaci tiketu → existující sledující jsou vidět jako chipy.
2. Přidej dalšího sledujícího, odeber původního, ulož.
3. Ověř v detailu tiketu, že seznam je správný.

Scénář 3 — notifikace (volitelné, v dev prostředí s konzolou):
1. V `local.py` dočasně nastav `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`.
2. Přidej komentář k tiketu se sledujícím → v konzoli se zobrazí e-mail adresovaný i sledujícímu.

- [ ] **Krok 3: Aktualizovat memory backlog**

Označ položku „Sledující (watchers)" jako dokončenou v `project_backlog.md` v paměti.
