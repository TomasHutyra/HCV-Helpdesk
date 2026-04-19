# HCV Helpdesk — Design dokument

Popis implementace, použitých nástrojů, vývojového a produkčního prostředí.

---

## Technologický stack

### Backend

**Django 5.x**
Hlavní web framework. Zajišťuje ORM (přístup k databázi), šablonovací systém, URL routing, autentizaci, formuláře, správu migrací a Django Admin. Projekt používá vlastní model uživatele (`AUTH_USER_MODEL = 'accounts.User'`), který rozšiřuje vestavěný `AbstractUser`.

**django-fsm**
Knihovna pro stavové automaty. Stav tiketu je FSM pole — knihovna definuje povolené přechody jako dekorátory na metodách modelu (`@transition`). Pokus o nepovolený přechod vyvolá výjimku. Tím je stavová logika centralizována v modelu a nelze ji obejít z view ani konzole.

**django-environ**
Načítá konfiguraci ze souboru `.env` a proměnných prostředí. Umožňuje typově bezpečné čtení hodnot (bool, int, seznam, URL databáze). Díky tomu jsou všechny citlivé hodnoty (hesla, klíče, adresy) mimo kód a mimo git.

**django-htmx**
Přidává middleware, který nastavuje `request.htmx` na každý HTTP požadavek. View tak snadno pozná, zda jde o HTMX požadavek (partial refresh) nebo plný page load, a vrátí odpovídající odpověď.

**WhiteNoise**
Middleware, který obsluhuje statické soubory přímo z Gunicorna bez nutnosti Nginx pro `/static/`. V produkci používá `CompressedManifestStaticFilesStorage` — při `collectstatic` přidá do názvů souborů hash obsahu, takže prohlížeče vždy dostanou aktuální verzi a lze nastavit dlouhé cache hlavičky.

### Frontend

**HTMX**
JavaScript knihovna načtená z CDN. Umožňuje přidávat interaktivitu HTML atributy (`hx-post`, `hx-target`, `hx-swap`) — kliknutí na tlačítko odešle AJAX požadavek na server a výsledkem nahradí část stránky. Využíváno pro všechny akce na detailu tiketu: přiřazení řešitele/obchodníka, přidání komentáře, zápis času, upload/smazání přílohy. Stránka se tedy neobnovuje celá.

**Alpine.js**
Odlehčený JavaScript framework načtený z CDN. Používá se pro čistě klientskou interaktivitu, která nevyžaduje server: rozbalovací panel Historie změn (`x-show`, `x-data`) a podmíněné zobrazení polí formuláře uživatele dle zaškrtnutých rolí (`x-init`, `@change`).

### Databáze

**SQLite** (lokální vývoj)
Souborová databáze vestavěná v Pythonu. Nevyžaduje instalaci, vhodná pro vývoj. Soubor `db.sqlite3` je v `.gitignore`.

**PostgreSQL 16** (produkce)
Plnohodnotná relační databáze. Běží jako Docker kontejner `db` s perzistentním svazkem `postgres_data`. Připojení je konfigurováno přes `DATABASE_URL` v `.env.production`.

### Asynchronní úlohy

**Celery 5**
Framework pro asynchronní a periodické úlohy. Aplikace ho využívá dvojím způsobem:
- **Notifikační tasky** — view po akci (vytvoření tiketu, přidání komentáře, …) zavolá `task.delay(pk)`. Celery task pak načte data z DB a odešle e-mail. Díky tomu HTTP odpověď uživateli nečeká na odeslání e-mailu.
- **Periodické tasky** — Celery Beat spouští `poll_imap_inbox` každé 2 minuty.

**Redis 7**
Slouží jako Celery broker (fronta zpráv mezi web serverem a workerem) a Celery result backend (ukládání výsledků tasků). V produkci ho Django také využívá jako cache backend (deduplikace a rate limiting IMAP pollingu). Běží jako Docker kontejner `redis`.

### Produkční serving

**Gunicorn**
WSGI server. Spouští 3 worker procesy, každý obsluhuje HTTP požadavky. Komunikuje s Nginx přes interní Docker síť na portu 8000.

**Nginx**
Reverzní proxy před Gunicornem. Zajišťuje SSL terminaci (Let's Encrypt), servírování statických souborů a mediálních souborů přímo ze sdílených Docker svazků (bez zatěžování Gunicorna), a blokuje přímý přístup k přílohám tiketů přes URL.

**Docker + Docker Compose**
Celý produkční stack běží v kontejnerech definovaných v `docker-compose.yml`. Každá služba má vlastní kontejner; sdílené soubory (media, staticfiles) jsou Docker named volumes. Kontejnery mají `restart: unless-stopped` — po restartu serveru se spustí automaticky.

### Python závislosti (`requirements.txt`)

| Balíček | Účel |
|---------|------|
| `Django` | Web framework |
| `django-environ` | Konfigurace z `.env` a proměnných prostředí |
| `django-fsm` | Stavový automat tiketů |
| `django-htmx` | Detekce HTMX požadavků v Django views |
| `whitenoise` | Servírování statických souborů z Gunicorna |
| `gunicorn` | WSGI server pro produkci |
| `psycopg2-binary` | PostgreSQL driver pro Django ORM |
| `celery` | Asynchronní a periodické úlohy |
| `redis` | Python klient pro Redis (Celery + cache) |
| `imapclient` | IMAP polling příchozích e-mailů |
| `Pillow` | Zpracování obrázků při nahrávání příloh |
| `openpyxl` | Sestavení XLSX souboru pro export tiketů |

---

## Struktura projektu

```
HCV_Helpdesk/
├── helpdesk/               # Konfigurační balíček Django projektu
│   ├── settings/
│   │   ├── base.py         # Společná konfigurace (všechna prostředí)
│   │   ├── local.py        # Přepisy pro lokální vývoj (SQLite, eager Celery)
│   │   └── production.py   # Přepisy pro produkci (PostgreSQL, Redis cache, HTTPS)
│   ├── urls.py             # Kořenové URL routování
│   ├── celery.py           # Inicializace Celery aplikace
│   └── wsgi.py             # WSGI entry point pro Gunicorn
│
├── apps/
│   ├── accounts/           # Uživatelé, role, firmy, oblasti
│   ├── tickets/            # Tikety, komentáře, přílohy, záznamy času, audit log
│   ├── notifications/      # E-mailové notifikace, IMAP polling, Celery tasky
│   └── stats/              # Statistiky (dashboard pro řešitele a správce)
│
├── templates/              # Všechny HTML šablony (globální adresář)
│   ├── base.html           # Základní layout (sidebar, topbar)
│   ├── accounts/           # Šablony pro uživatele, firmy, oblasti
│   ├── tickets/            # Šablony pro tikety
│   │   └── partials/       # HTMX partials (komentáře, přílohy, časové záznamy, …)
│   └── stats/              # Šablony pro dashboard
│
├── static/
│   └── css/app.css         # Veškeré CSS (design system, utility třídy)
│
├── nginx/nginx.conf        # Nginx konfigurace pro produkci
├── docker-compose.yml      # Definice Docker služeb
├── Dockerfile              # Build image pro web/worker/beat
├── requirements.txt        # Python závislosti
├── HCV_Helpdesk.md         # Funkční specifikace
└── DESIGN.md               # Tento soubor
```

---

## Datový model

### `apps.accounts`

**`User`** — rozšiřuje `AbstractUser`:
- `email` — unikátní, slouží jako přihlašovací identifikátor i pro notifikace
- `company` — FK na `Company` (povinné u Žadatele)
- `language` — preferovaný jazyk rozhraní (`cs` / `en`)
- `managed_areas` — M2M na `Area`; omezení viditelnosti tiketů pro Správce
- `managed_companies` — M2M na `Company`; omezení viditelnosti tiketů pro Správce
- `resolver_areas` — M2M na `Area`; omezení viditelnosti nových tiketů pro Řešitele

Role jsou odděleny do modelu **`UserRole`** (M2M přes samostatnou tabulku), aby jeden uživatel mohl mít více rolí najednou. Dostupné role: `requester`, `resolver`, `sales`, `manager`, `admin`.

**`Company`** — firma spravovaného zákazníka.

**`Area`** (`apps.tickets.Area`) — oblast tiketu (IT, Helios, …); příznak `is_unknown` označuje oblast pro tikety přijaté e-mailem bez klasifikace.

### `apps.tickets`

**`Ticket`** — hlavní entita:
- Typ: `problem` / `development` / `improvement`
- Stav: FSM pole (`django-fsm`), platné přechody závisí na typu tiketu
- Priority: `high` / `medium` / `low`
- FK: `requester`, `resolver`, `sales`, `company`, `area`
- `resolution_notes`, `rejection_reason` — vyplňují se při uzavření

**Stavový automat** (`django-fsm`):
```
Hlášení problému:    Nový → Řeší se → Vyřešeno
                     * → Zamítnuto

Požadavek na vývoj:  Nový → Příprava nabídky → Řeší se → Vyřešeno
                     * → Zamítnuto

Námět na zlepšení:   Nový
                     * → Zamítnuto
```
Uzamčené stavy (`Vyřešeno`, `Zamítnuto`) povolují pouze přechod zpět na `Řeší se` / `Příprava nabídky`.

**`Comment`** — komentář k tiketu (autor, text, čas).

**`TimeLog`** — záznam odpracovaného času (uživatel, hodiny, poznámka).

**`TicketAttachment`** — příloha; soubor uložen do `media/tickets/attachments/` pod UUID názvem, originální název v DB.

**`TicketChange`** — auditní log; každá změna stavu, pole, přiřazení, přílohy je zaznamenána (pole, stará hodnota, nová hodnota, autor, čas).

---

## Aplikační vrstvy

### Views (`apps/tickets/views.py`, `apps/accounts/views.py`)

Používají Django class-based views (`ListView`, `DetailView`, `CreateView`, `UpdateView`) a prosté `View` pro HTMX akce.

Přístupová kontrola je implementována přímo ve view metodách (`dispatch`, `get_object`) pomocí pomocných funkcí:
- `_manager_has_ticket_access(user, ticket)` — kontrola omezení správce
- `user.can_see_ticket_as_manager(ticket)` — metoda na modelu User
- `user.can_handle_ticket_area(ticket)` — metoda na modelu User (omezení řešitele)

### HTMX

Interaktivní akce na detailu tiketu (přiřazení řešitele, přidání komentáře, nahrání přílohy, zápis času, …) jsou implementovány jako samostatné URL endpointy, které vracejí HTML partial. HTMX je zahrnuto z CDN v `base.html`. Django middleware `HtmxMiddleware` přidává `request.htmx` pro detekci HTMX požadavků.

### Alpine.js

Slouží pro klientskou interaktivitu bez nutnosti volání serveru:
- Rozbalovací panel Historie změn na detailu tiketu
- Podmíněné zobrazení polí „Spravované oblasti/firmy" a „Oblasti řešitele" na formuláři uživatele dle zaškrtnutých rolí

---

## Asynchronní úlohy a e-maily (Celery)

Celery aplikace je definována v `helpdesk/celery.py`. Všechny tasky jsou v `apps/notifications/tasks.py`.

### Jak funguje odesílání notifikací

Když uživatel provede akci (vytvoří tiket, přidá komentář, …), view zavolá Celery task metodou `.delay(pk)`. Ta vloží zprávu do fronty v Redis. HTTP odpověď uživateli je okamžitě odeslána — nečeká na e-mail.

Kontejner `worker` (Celery worker) sleduje frontu v Redis. Jakmile se ve frontě objeví zpráva, worker ji vyzvedne, načte potřebná data z PostgreSQL a odešle e-mail přes SMTP. Worker běží jako samostatný proces nezávisle na web serveru.

```
Uživatel → HTTP požadavek → Django view
                                 │
                          task.delay(pk)  ←→  Redis (fronta)
                                                    │
                                              Celery worker
                                                    │
                                               SMTP server → příjemce
```

### Notifikační tasky

| Task | Spouštěč |
|------|----------|
| `notify_new_ticket` | Vytvoření tiketu (web formulář i e-mailem) |
| `notify_status_change` | Změna stavu na Řeší se / Příprava nabídky |
| `notify_assigned_to_resolver` | Přiřazení řešitele |
| `notify_assigned_to_sales` | Přiřazení obchodníka |
| `notify_new_comment` | Přidání komentáře |
| `notify_ticket_closed` | Vyřešení nebo zamítnutí tiketu |

### Jak funguje automatická kontrola příchozích e-mailů

Kontejner `beat` (Celery Beat) drží interní plán úloh a každé 2 minuty vloží do fronty v Redis zprávu `poll_imap_inbox`. Worker ji vyzvedne a spustí `process_inbox()` z `apps/notifications/imap_polling.py`.

```
Celery Beat (každé 2 min)
        │
   poll_imap_inbox  →  Redis (fronta)
                              │
                        Celery worker
                              │
                       imap_polling.process_inbox()
                              │
                        IMAP server (SSL)
                              │
                    pro každý UNSEEN e-mail:
                      1. deduplikace (Message-ID → cache)
                      2. ověření odesílatele (DB lookup)
                      3. rate limiting (cache počítadlo)
                      4. vytvoření tiketu v PostgreSQL
                      5. uložení příloh na disk (media svazek)
                      6. notify_new_ticket.delay(pk) → fronta
                      7. označit e-mail jako SEEN
```

`beat` a `worker` jsou oddělené kontejnery záměrně — Beat pouze plánuje, Worker vykonává. Díky tomu lze worker škálovat horizontálně (více instancí) bez změny Beatu.

### Periodické tasky (Celery Beat)

| Task | Interval | Definice |
|------|----------|---------|
| `poll_imap_inbox` | každé 2 minuty | `settings/base.py` → `CELERY_BEAT_SCHEDULE` |

---

## Konfigurace projektu

Konfigurace je rozdělena do tří souborů ve `helpdesk/settings/`. Aktivní soubor se vybírá proměnnou prostředí `DJANGO_SETTINGS_MODULE`. Všechny citlivé hodnoty se načítají z `.env` přes `django-environ` — nikdy nejsou přímo v kódu.

### `base.py` — společná konfigurace

Obsahuje vše, co se nemění mezi prostředími:
- `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`
- `AUTH_USER_MODEL`, přihlašovací URL
- Validátory hesel
- Jazyk (`cs`), časové pásmo (`Europe/Prague`), i18n
- Statické soubory (`STATIC_URL`, `STATICFILES_STORAGE` = WhiteNoise)
- Media soubory (`MEDIA_URL`, `MEDIA_ROOT`)
- E-mailová konfigurace (SMTP) — načítaná z `.env`
- IMAP konfigurace — načítaná z `.env`
- Cache: výchozí `LocMemCache` (production přepíše na Redis)
- `IMAP_RATE_LIMIT = 10` (tikety/hod na odesílatele)
- Celery: broker, backend, plán (`CELERY_BEAT_SCHEDULE`)

### `local.py` — lokální vývoj

```python
from .base import *

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Celery tasky se spouštějí synchronně — Redis není potřeba
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

Co to znamená v praxi:
- **SQLite** — stačí soubor, žádná instalace databáze
- **`CELERY_TASK_ALWAYS_EAGER`** — `task.delay()` se nevolá asynchronně, ale okamžitě synchronně v procesu Djanga; výsledek (odeslaný e-mail) je vidět ihned, Redis ani worker nejsou potřeba
- **Cache** — `LocMemCache` z `base.py`; deduplikace a rate limiting IMAP fungují, ale cache je in-process a reset při restartu

### `production.py` — produkce

```python
from .base import *

DEBUG = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('CELERY_BROKER_URL', default='redis://redis:6379/0'),
    }
}

DATABASES = {
    'default': env.db('DATABASE_URL')  # postgres://helpdesk:...@db:5432/hcv_helpdesk
}

# HTTPS hlavičky
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session — 8 hodin, konec po zavření prohlížeče
SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

Co to znamená v praxi:
- **PostgreSQL** — připojení přes `DATABASE_URL` z `.env.production`
- **Redis cache** — deduplikace a rate limiting IMAP sdílí cache mezi všemi procesy (web, worker, beat) přes Redis; klíče přežijí restart kontejnerů
- **HTTPS vynucení** — Django přesměruje HTTP → HTTPS i za Nginxem; bezpečné cookie hlavičky
- **HSTS** — prohlížeč si zapamatuje, že doména vyžaduje HTTPS, po dobu 1 roku

### Soubor `.env.production` (na serveru, mimo git)

```
DJANGO_SETTINGS_MODULE=helpdesk.settings.production
SECRET_KEY=<dlouhý náhodný řetězec>
DEBUG=False
ALLOWED_HOSTS=helpdesk.hcvdesk.eu
DATABASE_URL=postgres://helpdesk:<heslo>@db:5432/hcv_helpdesk
POSTGRES_PASSWORD=<heslo>
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<smtp server>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<smtp uživatel>
EMAIL_HOST_PASSWORD=<smtp heslo>
DEFAULT_FROM_EMAIL=helpdesk@hcvdesk.eu
HELPDESK_EMAIL=helpdesk@hcvdesk.eu
IMAP_HOST=<imap server>
IMAP_PORT=993
IMAP_USE_SSL=True
IMAP_USER=<imap uživatel>
IMAP_PASSWORD=<imap heslo>
IMAP_FOLDER=INBOX
```

---

## Produkce

### Infrastruktura

Server: **Hetzner Cloud** (Ubuntu), IP `178.104.13.134`
Doména: `helpdesk.hcvdesk.eu`
SSL: Let's Encrypt (Certbot)
Pracovní adresář: `/root/HCV-Helpdesk`

### Docker Compose služby

```
nginx    — reverzní proxy, SSL terminace, statické soubory
web      — Gunicorn (3 workers), port 8000 (interní)
worker   — Celery worker (zpracování asynchronních úloh)
beat     — Celery Beat (plánování periodických tasků)
db       — PostgreSQL 16
redis    — Redis 7 (Celery broker + backend + cache)
```

### Nginx

- HTTP (port 80) → redirect na HTTPS
- HTTPS (port 443) s Let's Encrypt certifikátem
- `/static/` → přímo ze svazku `staticfiles_data` (30denní cache)
- `/media/` → přímo ze svazku `media_data`
- `/media/tickets/attachments/` → **zakázáno** (`deny all`) — přílohy tiketů jsou dostupné výhradně přes Django view, které ověřuje oprávnění
- Ostatní → proxy na `web:8000`

### Gunicorn

3 workers, timeout 120 s, logy na stdout (sbírá Docker).

### Nasazení nové verze

```bash
ssh root@178.104.13.134
cd /root/HCV-Helpdesk
git pull
docker compose up --build -d web worker beat
# Pokud jsou nové migrace:
docker compose exec web python manage.py migrate
# Pokud jsou nové statické soubory:
docker compose exec web python manage.py collectstatic --noinput
```

### Ověření po nasazení

```bash
docker compose ps                        # všechny kontejnery running?
docker compose logs web --tail=20        # chyby v aplikaci?
docker compose logs worker --tail=20     # chyby v Celery?
```

---

## Překlady (i18n)

Rozhraní je připraveno pro češtinu a angličtinu. Přeložitelné řetězce jsou označeny `gettext_lazy(_(...))`. Jazyk si každý uživatel volí v profilu; preference je uložena v poli `User.language` a nastavena jako cookie při přihlášení.

```bash
# Extrakce řetězců do .po souborů
python manage.py makemessages -l cs -l en

# Kompilace .po → .mo
python manage.py compilemessages
```

Soubory překladů: `locale/cs/LC_MESSAGES/django.po` a `locale/en/LC_MESSAGES/django.po`.
