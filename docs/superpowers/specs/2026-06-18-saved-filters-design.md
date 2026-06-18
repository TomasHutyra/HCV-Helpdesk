# Uložené filtry — design spec

## Cíl

Uživatel si zapamatuje nastavení filtru v přehledu tiketů tak, aby:
1. **Automatická persistence** — po navigaci pryč a zpět se filtry obnoví (localStorage).
2. **Pojmenované filtry** — uživatel si uloží filtr pod názvem, přepíná mezi nimi (DB, osobní per-user).

## 1. Automatická persistence (localStorage)

### Chování

- Při odeslání filter-formu JS uloží GET parametry (včetně `sort`, `dir`) do `localStorage` pod klíč `ticketFilters`.
- Při příchodu na `/tickets/` **bez** GET parametrů (klik z menu, přímá URL):
  - JS zkontroluje localStorage.
  - Pokud tam filtr je → `window.location.search = uložené_parametry` (přesměrování).
- Při příchodu **s** GET parametry → localStorage se aktualizuje na aktuální parametry.
- Tlačítko "Reset" smaže localStorage klíč `ticketFilters`.
- Parametr `page` se **ne**persistuje (vždy stránka 1).

### Implementace

Čistý JavaScript v `ticket_list.html` — žádný dopad na backend.

## 2. Pojmenované filtry — datový model

### Model `SavedFilter`

Umístění: `apps/tickets/models.py`

```python
class SavedFilter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_filters')
    name = models.CharField(max_length=100)
    params = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = [('user', 'name')]
```

- `params` ukládá GET parametry jako dict: `{"status": "open", "area": "3", "sort": "priority", "dir": "asc"}`.
- `unique_together` brání duplicitním názvům u jednoho uživatele.
- Žádný limit na počet filtrů.

## 3. API endpointy

Všechny vyžadují `LoginRequiredMixin`. Umístění: `apps/tickets/views.py`, registrace v `apps/tickets/urls.py`.

| Endpoint | Metoda | Akce | Request | Response |
|----------|--------|------|---------|----------|
| `POST /tickets/filters/save/` | AJAX | Uloží / přepíše filtr | `{"name": "...", "params": {...}}` | `{"id": 1, "name": "..."}` |
| `DELETE /tickets/filters/<id>/delete/` | AJAX | Smaže filtr (jen vlastní) | — | `{"ok": true}` |
| `GET /tickets/filters/` | AJAX | Seznam filtrů uživatele | — | `[{"id": 1, "name": "...", "params": {...}}]` |

- Save endpoint: `update_or_create(user=user, name=name, defaults={"params": params})`.
- Delete endpoint: `get_object_or_404(SavedFilter, pk=id, user=user).delete()`.

## 4. Aplikace filtru

Čistě klientská — JS vezme `params` z uloženého filtru a přesměruje:
```js
window.location.href = '/tickets/?' + new URLSearchParams(filter.params)
```

Stávající `TicketListView` zpracuje GET parametry beze změny.

## 5. UI

### Umístění

Dropdown tlačítko vedle stávajících "Filtrovat / Reset / Export XLSX":

```
[Filtrovat] [Reset] [Export XLSX] [▾ Uložené filtry]
```

### Dropdown obsah

1. **"Uložit aktuální filtr…"** — kliknutí → inline input pro zadání názvu → AJAX POST `/tickets/filters/save/`.
2. **Seznam uložených filtrů** — klik na název → přesměrování na URL s params.
3. **Ikonka ✕** u každého filtru → confirm dialog → AJAX DELETE.

Pokud nejsou žádné filtry, dropdown zobrazí jen "Uložit aktuální filtr…".

### Implementace

- Alpine.js (`x-data`, `@click.away`).
- Lazy loading: při prvním otevření dropdownu AJAX GET `/tickets/filters/`. Data kešována v Alpine state, invalidace po uložení/smazání.
- Stylování: stávající design system (`.btn-secondary`, dropdown styl konzistentní s existujícími dropdowny v projektu).

## 6. Co se NEMĚNÍ

- Stávající `TicketFilterForm`, `_apply_ticket_filters`, `TicketListView.get_queryset` — beze změny.
- Stávající GET parametry fungují jako dnes.
- Export XLSX — beze změny.
- Žádné sdílené filtry, žádný rename (smazat + uložit znovu).
