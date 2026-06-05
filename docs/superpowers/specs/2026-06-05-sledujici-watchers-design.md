# Design: Sledující (Watchers)

**Datum:** 2026-06-05  
**Stav:** schváleno

---

## Přehled

Sledující jsou osoby (registrovaní uživatelé nebo externí e-maily), které dostávají e-mailové notifikace o dění na tiketu, aniž by byly přiřazeny jako žadatel, řešitel nebo obchodník. Sledující se spravují ve formuláři při zakládání a editaci tiketu.

---

## 1. Datový model

Nový model `TicketWatcher` v `apps/tickets/models.py`.

```python
class TicketWatcher(models.Model):
    ticket = ForeignKey(Ticket, CASCADE, related_name='ticket_watchers')
    email  = EmailField()
    name   = CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [('ticket', 'email')]
        ordering = ['name', 'email']
```

- E-mail je přirozený klíč — `unique_together` garantuje deduplikaci na DB úrovni.
- Při přidání existujícího uživatele: `name = user.get_full_name()`, `email = user.email`.
- Při přidání externího e-mailu: `name = ''`.
- Migrace: `0014_ticketwatcher`.

---

## 2. Formuláře

### Pole `watchers`

Do `TicketCreateForm` i `TicketUpdateForm` přibyde skryté pole `watchers` (CharField, not required). Uchovává comma-separated seznam e-mailů.

Widget se renderuje v šabloně jako vlastní HTML blok:

```html
<!-- Sledující -->
<label>Sledující</label>
<div>
  <input type="text" id="watcher-input" list="watcher-suggestions"
         placeholder="e-mail nebo jméno…">
  <datalist id="watcher-suggestions">
    <!-- aktivní uživatelé: value="email" label="Jméno Příjmení" -->
  </datalist>
  <button type="button" onclick="addWatcher()">+ Přidat</button>
</div>
<div id="watcher-chips">
  <!-- chip pro každého sledujícího: [Jméno / email  ×] -->
</div>
<input type="hidden" name="watchers" id="watchers-hidden">
```

Vanilla JS (~25 řádků) obsluhuje:
- `addWatcher()` — validace e-mailu, přidání chipu, sync hidden fieldu.
- Klik na `×` — odebrání chipu, sync hidden fieldu.
- Inicializace — při renderování editačního formuláře předvyplnění chipů z existujících `TicketWatcher` záznamů.

### Kdo vidí pole

- Žadatel: vidí pole při **zakládání** tiketu. Při editaci tiketu žadatel pole nevidí (žadatel nemá přístup k `TicketUpdateForm`).
- Staff (řešitel, správce, admin): vidí pole při **editaci** tiketu.

### Zpracování v pohledech

**TicketCreateView.form_valid()** — po uložení tiketu:
```
emails = parse comma-separated watchers field
for each email:
    user = User.objects.filter(email=email).first()
    TicketWatcher.objects.get_or_create(
        ticket=ticket, email=email,
        defaults={'name': user.get_full_name() if user else ''}
    )
```

**TicketUpdateView.form_valid()** — sync:
```
new_emails = set(parse watchers field)
ticket.ticket_watchers.exclude(email__in=new_emails).delete()
for each email in new_emails:
    TicketWatcher.objects.get_or_create(ticket=ticket, email=email, ...)
```

---

## 3. Notifikace

Helper v `apps/notifications/email.py`:
```python
def _get_watcher_emails(ticket):
    return list(ticket.ticket_watchers.values_list('email', flat=True))
```

Úpravy existujících funkcí — sledující se přidají do příjemců **deduplikovaně** s ostatními a s výjimkou autora akce:

| Funkce | Sledující dostávají? | Poznámka |
|---|---|---|
| `send_new_ticket` | ano | přidáni do `recipients` |
| `send_status_change` | ano | přidáni do `recipients` |
| `send_new_comment` | ano | autor komentáře vyloučen i pokud je sledující |
| `send_ticket_closed` | ano | přidáni do `recipients` |
| `send_rating_request` | **ne** | osobní výzva jen žadateli |
| `send_assigned_to_you` | **ne** | osobní notifikace přiřazenému |

---

## 4. Detail tiketu — postranní sloupec

Sledující se zobrazí v postranním sloupci jako read-only seznam (pod nebo vedle sekce Kontaktní osoba). Sekce se renderuje jen pokud `ticket.ticket_watchers.exists()`.

```
Sledující
  Jan Novák
  eva@ext.cz
```

Sekci vidí žadatel i staff. Správa sledujících probíhá výhradně přes formulář editace tiketu — žádná inline HTMX akce v detailu.

---

## 5. Mimo rozsah

- Audit log sledujících (TicketChange záznamy) — není implementováno.
- Opt-out odkaz v e-mailu pro sledující — není implementováno.
- Sledující na IMAP příchozím tiketu — není implementováno.
