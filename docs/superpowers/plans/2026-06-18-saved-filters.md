# Uložené filtry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users persist ticket list filters across navigation (localStorage) and save/load named filters (DB).

**Architecture:** Two layers — (1) client-side localStorage auto-saves GET params on every filter submission and restores them when the user navigates back to `/tickets/` without params; (2) server-side `SavedFilter` model with three JSON API endpoints (list/save/delete) + Alpine.js dropdown in the filter bar for managing named filters.

**Tech Stack:** Django 5.x, Alpine.js 3.x (already in base.html CDN), vanilla JS, SQLite (local) / PostgreSQL (prod), `models.JSONField`.

## Global Constraints

- Tests run via `python manage.py test apps.tickets.tests --settings=helpdesk.settings.local`
- Czech UI labels, English code
- CSRF token available via `document.querySelector('body').getAttribute('hx-headers')` → parse JSON → `X-CSRFToken`
- Alpine.js already loaded globally (base.html CDN)
- Existing patterns: `LoginRequiredMixin` + `View`, test helpers `_company()`, `_area()`, `_user()`, `_ticket()` in `apps/tickets/tests.py`

---

### Task 1: SavedFilter model + migration

**Files:**
- Modify: `apps/tickets/models.py` (append model at end)
- Create migration via `makemigrations`

**Interfaces:**
- Produces: `SavedFilter` model with fields `user` (FK→User), `name` (CharField 100), `params` (JSONField), `created_at` (DateTimeField). `Meta: ordering=['name'], unique_together=[('user','name')]`.

- [ ] **Step 1: Write the failing test**

Add to `apps/tickets/tests.py`:

```python
from apps.tickets.models import SavedFilter


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.tickets.tests.SavedFilterModelTest --settings=helpdesk.settings.local -v2`
Expected: Error — `SavedFilter` not found in models.

- [ ] **Step 3: Implement SavedFilter model**

Append to `apps/tickets/models.py`:

```python
class SavedFilter(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='saved_filters', verbose_name=_('uživatel'),
    )
    name = models.CharField(_('název'), max_length=100)
    params = models.JSONField(_('parametry'), default=dict)
    created_at = models.DateTimeField(_('vytvořeno'), auto_now_add=True)

    class Meta:
        verbose_name = _('uložený filtr')
        verbose_name_plural = _('uložené filtry')
        ordering = ['name']
        unique_together = [('user', 'name')]

    def __str__(self):
        return f'{self.name} ({self.user})'
```

- [ ] **Step 4: Create and run migration**

Run:
```bash
python manage.py makemigrations tickets --settings=helpdesk.settings.local
python manage.py migrate --settings=helpdesk.settings.local
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.tickets.tests.SavedFilterModelTest --settings=helpdesk.settings.local -v2`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/tickets/models.py apps/tickets/tests.py apps/tickets/migrations/
git commit -m "feat: SavedFilter model — uložené filtry per uživatel"
```

---

### Task 2: API endpoints (list, save, delete)

**Files:**
- Modify: `apps/tickets/views.py` (add 3 view classes)
- Modify: `apps/tickets/urls.py` (add 3 URL patterns)
- Modify: `apps/tickets/tests.py` (add API tests)

**Interfaces:**
- Consumes: `SavedFilter` model from Task 1
- Produces:
  - `SavedFilterListView.get(request) → JsonResponse([{"id":int,"name":str,"params":dict}])`
  - `SavedFilterSaveView.post(request) → JsonResponse({"id":int,"name":str})` — body: `{"name":str,"params":dict}`
  - `SavedFilterDeleteView.delete(request, pk) → JsonResponse({"ok":true})`
  - URL names: `tickets:filter_list`, `tickets:filter_save`, `tickets:filter_delete`

- [ ] **Step 1: Write failing tests**

Add to `apps/tickets/tests.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.tickets.tests.SavedFilterAPITest --settings=helpdesk.settings.local -v2`
Expected: 404 errors — URLs not registered yet.

- [ ] **Step 3: Implement the three views**

Add to `apps/tickets/views.py` (imports at top: `import json` and `from django.http import JsonResponse`):

```python
class SavedFilterListView(LoginRequiredMixin, View):
    def get(self, request):
        filters = SavedFilter.objects.filter(user=request.user)
        data = [
            {'id': f.pk, 'name': f.name, 'params': f.params}
            for f in filters
        ]
        return JsonResponse(data, safe=False)


class SavedFilterSaveView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        name = body.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
        params = body.get('params', {})
        sf, _ = SavedFilter.objects.update_or_create(
            user=request.user, name=name,
            defaults={'params': params},
        )
        return JsonResponse({'id': sf.pk, 'name': sf.name})


class SavedFilterDeleteView(LoginRequiredMixin, View):
    def delete(self, request, pk):
        sf = get_object_or_404(SavedFilter, pk=pk, user=request.user)
        sf.delete()
        return JsonResponse({'ok': True})
```

- [ ] **Step 4: Add URL patterns**

Add to `apps/tickets/urls.py` (before the `<int:pk>/` patterns to avoid conflicts):

```python
    path('filters/', views.SavedFilterListView.as_view(), name='filter_list'),
    path('filters/save/', views.SavedFilterSaveView.as_view(), name='filter_save'),
    path('filters/<int:pk>/delete/', views.SavedFilterDeleteView.as_view(), name='filter_delete'),
```

- [ ] **Step 5: Add necessary imports to views.py**

Add at top of `apps/tickets/views.py`:

```python
import json
from django.http import JsonResponse
```

And add `SavedFilter` to the import from models:

```python
from .models import Ticket, Comment, TimeLog, Area, WorkCategory, SavedFilter, ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.tickets.tests.SavedFilterAPITest --settings=helpdesk.settings.local -v2`
Expected: All 8 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/tickets/views.py apps/tickets/urls.py apps/tickets/tests.py
git commit -m "feat: API endpointy pro uložené filtry (list/save/delete)"
```

---

### Task 3: localStorage persistence + saved-filters dropdown UI

**Files:**
- Modify: `templates/tickets/ticket_list.html` (add JS for localStorage + Alpine dropdown)
- Modify: `static/css/app.css` (add dropdown styles)

**Interfaces:**
- Consumes: API endpoints from Task 2 (`/tickets/filters/`, `/tickets/filters/save/`, `/tickets/filters/<id>/delete/`)
- Produces: Fully functional UI — localStorage persistence + saved filters dropdown

- [ ] **Step 1: Add localStorage persistence JS**

In `templates/tickets/ticket_list.html`, replace the existing `<script>` block (lines 76–94, the export-href updater) with a combined script that handles both export-href updating AND localStorage persistence. Place it right after the closing `</form>` tag of the filter bar:

```javascript
<script>
(function () {
  var STORAGE_KEY = 'ticketFilters';
  var form = document.querySelector('.filter-bar');
  var btn = document.getElementById('export-btn');

  // --- Export href updater (existing logic) ---
  function updateExportHref() {
    var base = btn.href.split('?')[0];
    var params = new URLSearchParams(new FormData(form));
    var current = new URLSearchParams(window.location.search);
    ['sort', 'dir'].forEach(function(k) {
      if (current.has(k)) params.set(k, current.get(k));
      else params.delete(k);
    });
    btn.href = base + (params.toString() ? '?' + params.toString() : '');
  }
  updateExportHref();
  form.addEventListener('change', updateExportHref);
  form.addEventListener('input', updateExportHref);

  // --- localStorage persistence ---
  var search = window.location.search;
  if (search && search !== '?') {
    // Page loaded with GET params → save them (strip leading '?')
    var p = new URLSearchParams(search);
    p.delete('page');
    localStorage.setItem(STORAGE_KEY, p.toString());
  } else {
    // No GET params → restore from localStorage if available
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      window.location.search = '?' + saved;
    }
  }
})();
</script>
```

- [ ] **Step 2: Wire up the Reset button to clear localStorage**

Change the Reset `<a>` tag in the filter bar from:

```html
<a href="{% url 'tickets:list' %}" class="btn btn-secondary btn-sm">{% trans "Reset" %}</a>
```

to:

```html
<a href="{% url 'tickets:list' %}" class="btn btn-secondary btn-sm"
   onclick="localStorage.removeItem('ticketFilters')">{% trans "Reset" %}</a>
```

- [ ] **Step 3: Add the saved-filters dropdown Alpine component**

In the filter bar, inside the `<div style="display:flex;gap:6px;align-items:flex-end">` that holds the buttons, add the dropdown after the Export button:

```html
<div x-data="savedFilters()" class="saved-filters-wrap">
  <button type="button" class="btn btn-secondary btn-sm" @click="toggle()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px;display:inline-block;vertical-align:-2px;margin-right:4px"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
    {% trans "Uložené filtry" %}
  </button>
  <div x-show="open" @click.away="open = false" x-cloak class="saved-filters-dropdown">
    <!-- Save current -->
    <div class="sf-save-row">
      <template x-if="!saving">
        <button type="button" class="sf-action-btn" @click="saving = true">
          {% trans "Uložit aktuální filtr…" %}
        </button>
      </template>
      <template x-if="saving">
        <form @submit.prevent="save()" class="sf-save-form">
          <input x-ref="nameInput" x-model="newName" type="text"
                 placeholder="{% trans 'Název filtru' %}" maxlength="100" class="sf-name-input">
          <button type="submit" class="btn btn-sky btn-sm">{% trans "Uložit" %}</button>
          <button type="button" class="btn btn-secondary btn-sm" @click="saving = false; newName = ''">✕</button>
        </form>
      </template>
    </div>
    <!-- Filter list -->
    <template x-if="filters.length > 0">
      <div class="sf-list">
        <template x-for="f in filters" :key="f.id">
          <div class="sf-item">
            <a :href="'/tickets/?' + new URLSearchParams(f.params).toString()"
               class="sf-item-name" x-text="f.name"
               @click="localStorage.setItem('ticketFilters', new URLSearchParams(f.params).toString())"></a>
            <button type="button" class="sf-item-delete" @click.stop="remove(f)"
                    :title="'{% trans "Smazat" %}'">✕</button>
          </div>
        </template>
      </div>
    </template>
  </div>
</div>
```

- [ ] **Step 4: Add the Alpine component JS**

Add a second `<script>` block (after the first one, before `{% endblock %}`):

```javascript
<script>
function savedFilters() {
  return {
    open: false,
    filters: [],
    loaded: false,
    saving: false,
    newName: '',
    csrfToken: JSON.parse(document.body.getAttribute('hx-headers'))['X-CSRFToken'],

    toggle() {
      this.open = !this.open;
      if (this.open && !this.loaded) this.load();
    },

    async load() {
      var resp = await fetch('/tickets/filters/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      this.filters = await resp.json();
      this.loaded = true;
    },

    async save() {
      var name = this.newName.trim();
      if (!name) return;
      var params = Object.fromEntries(new URLSearchParams(window.location.search));
      delete params.page;
      await fetch('/tickets/filters/save/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify({ name: name, params: params }),
      });
      this.newName = '';
      this.saving = false;
      this.loaded = false;
      await this.load();
    },

    async remove(f) {
      if (!confirm('Smazat filtr „' + f.name + '"?')) return;
      await fetch('/tickets/filters/' + f.id + '/delete/', {
        method: 'DELETE',
        headers: { 'X-CSRFToken': this.csrfToken },
      });
      this.filters = this.filters.filter(function(x) { return x.id !== f.id; });
    },
  };
}
</script>
```

- [ ] **Step 5: Add dropdown CSS**

Append to `static/css/app.css`:

```css
/* Saved filters dropdown */
.saved-filters-wrap { position: relative; }
.saved-filters-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 260px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r);
  box-shadow: var(--shadow-md);
  z-index: 50;
  padding: 6px 0;
}
.sf-save-row { padding: 6px 12px; border-bottom: 1px solid var(--c-border); }
.sf-action-btn {
  background: none; border: none; cursor: pointer;
  color: var(--c-brand); font-size: 13px; padding: 0;
}
.sf-action-btn:hover { text-decoration: underline; }
.sf-save-form { display: flex; gap: 4px; align-items: center; }
.sf-name-input {
  flex: 1; padding: 4px 8px; font-size: 13px;
  border: 1px solid var(--c-border); border-radius: var(--r);
}
.sf-list { max-height: 240px; overflow-y: auto; }
.sf-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 12px;
}
.sf-item:hover { background: var(--c-bg); }
.sf-item-name {
  flex: 1; font-size: 13px; color: var(--c-text); text-decoration: none;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sf-item-name:hover { color: var(--c-brand); }
.sf-item-delete {
  background: none; border: none; cursor: pointer;
  color: var(--c-text-light); font-size: 13px; padding: 2px 4px; margin-left: 8px;
  line-height: 1;
}
.sf-item-delete:hover { color: var(--c-red); }
```

- [ ] **Step 6: Manual test**

Run: `python manage.py runserver --settings=helpdesk.settings.local`

Test checklist:
1. Set filters (e.g. status=open, area=IT) → click "Filtrovat" → navigate to a ticket detail → click back to tickets list → **filters should be restored from localStorage**
2. Click "Reset" → filters cleared → navigate away and back → **no filters restored** (localStorage cleared)
3. Click "Uložené filtry" dropdown → "Uložit aktuální filtr…" → type "Moje IT" → click Uložit → **filter appears in dropdown**
4. Click the saved filter name → **redirected with correct params**
5. Click ✕ on saved filter → confirm → **filter removed from dropdown**
6. Log in as different user → **sees no filters** (personal only)

- [ ] **Step 7: Commit**

```bash
git add templates/tickets/ticket_list.html static/css/app.css
git commit -m "feat: localStorage persistence + dropdown pro uložené filtry"
```

---

### Task 4: Update documentation

**Files:**
- Modify: `HCV_Helpdesk.md` (add saved filters section)

**Interfaces:**
- Consumes: All prior tasks

- [ ] **Step 1: Update HCV_Helpdesk.md**

Add a section documenting the saved filters feature — localStorage persistence behavior and named filters (personal, DB-backed).

- [ ] **Step 2: Commit**

```bash
git add HCV_Helpdesk.md
git commit -m "docs: uložené filtry — HCV_Helpdesk.md"
```
