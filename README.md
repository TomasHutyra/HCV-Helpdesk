# HCV Helpdesk

Webový helpdesk systém pro evidenci a správu IT požadavků. Postaven na Django + HTMX + Tailwind CSS.

## Funkce

- **Role**: Žadatel, Řešitel, Obchodník, Správce, Administrátor (jeden uživatel může mít více rolí)
- **Typy tiketů**: Hlášení problému / Požadavek na vývoj / Námět na zlepšení
- **Stavový automat**: validované přechody stavů (django-fsm)
- **E-mailové notifikace**: nový tiket, změna stavu, komentář, vyřešení/zamítnutí
- **Příjem tiketů e-mailem**: IMAP polling každé 2 minuty (Celery Beat)
- **Statistiky**: měsíční přehledy per řešitel a per firma
- **Jazyky**: čeština a angličtina (i18n)

## Technický stack

| Vrstva | Technologie |
|--------|------------|
| Backend | Django 5 + Python 3.12 |
| Frontend | HTMX + Alpine.js + Tailwind CSS |
| Stavový automat | django-fsm |
| Asynchronní úlohy | Celery + Redis |
| Databáze (prod) | PostgreSQL |
| Databáze (dev) | SQLite |
| Nasazení | Docker Compose + Nginx |

---

## Lokální vývoj (bez Dockeru)

### Požadavky

- Python 3.12+
- Git

### Instalace

```bash
# 1. Naklonujte repozitář
git clone https://github.com/TomasHutyra/HCV-Helpdesk.git
cd HCV-Helpdesk

# 2. Vytvořte virtuální prostředí
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Nainstalujte závislosti
pip install -r requirements.txt

# 4. Vytvořte konfigurační soubor
cp .env.example .env
# Otevřete .env a nastavte SECRET_KEY (libovolný dlouhý řetězec)
```

### Konfigurace `.env` pro lokální vývoj

```env
DJANGO_SETTINGS_MODULE=helpdesk.settings.local
SECRET_KEY=vas-tajny-klic-minimalne-50-znaku
DEBUG=True
```

E-maily se lokálně zobrazují v konzoli (není potřeba SMTP). Redis ani Celery nejsou potřeba — tasky běží synchronně.

### Spuštění

```bash
# Migrace databáze
python manage.py makemigrations
python manage.py migrate

# Vytvoření administrátorského účtu
python manage.py createsuperuser

# Spuštění serveru
python manage.py runserver
```

Aplikace poběží na **http://127.0.0.1:8000**

Django Admin je dostupný na **http://127.0.0.1:8000/admin/**

---

## První kroky po spuštění

Přes Django Admin (`/admin/`) nebo sekci Uživatelé/Firmy v aplikaci:

1. **Vytvořit firmy** — `Admin → Firmy → Nová firma`
2. **Vytvořit uživatele** — `Admin → Uživatelé → Nový uživatel` a přiřadit jim role
3. **Přiřadit žadatele k firmám** — každý žadatel musí mít vybranou firmu

### Role a jejich oprávnění

| Role | Možnosti |
|------|----------|
| **Žadatel** | Zakládá tikety, vidí jen vlastní, přidává komentáře |
| **Řešitel** | Vidí přiřazené tikety, zapisuje čas, vyřeší tiket |
| **Obchodník** | Stejně jako řešitel, jen u typu „Požadavek na vývoj" |
| **Správce** | Vidí vše, přiřazuje, zamítá, vidí statistiky |
| **Administrátor** | Spravuje uživatele a firmy |

---

## Testování e-mailu (Seznam.cz)

Pro testování odchozích e-mailů přes Seznam.cz upravte `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seznam.cz
EMAIL_PORT=587
EMAIL_HOST_USER=vas-email@seznam.cz
EMAIL_HOST_PASSWORD=vas-heslo
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=vas-email@seznam.cz
HELPDESK_EMAIL=vas-email@seznam.cz
```

Pro příchozí e-maily (IMAP polling — vytváření tiketů z e-mailu):

```env
IMAP_HOST=imap.seznam.cz
IMAP_PORT=993
IMAP_USER=vas-email@seznam.cz
IMAP_PASSWORD=vas-heslo
IMAP_USE_SSL=True
```

Spuštění IMAP pollingu ručně (pro testování):

```bash
python manage.py shell -c "from apps.notifications.imap_polling import process_inbox; process_inbox()"
```

---

## Překlady (i18n)

```bash
# Vygenerovat/aktualizovat .po soubory
python manage.py makemessages -l cs -l en

# Přeložit v locale/cs/LC_MESSAGES/django.po a locale/en/...

# Zkompilovat
python manage.py compilemessages
```

---

## Produkční nasazení (Docker Compose)

### Požadavky

- Docker + Docker Compose
- VPS s Ubuntu (doporučeno: Hetzner CX22, ~5 €/měsíc)

### Konfigurace

```bash
# Zkopírujte a upravte produkční .env
cp .env.example .env.production
```

Minimální `.env.production`:

```env
DJANGO_SETTINGS_MODULE=helpdesk.settings.production
SECRET_KEY=vas-dlouhy-tajny-klic
DEBUG=False
ALLOWED_HOSTS=helpdesk.vase-domena.cz

DATABASE_URL=postgres://helpdesk:POSTGRES_HESLO@db:5432/hcv_helpdesk
POSTGRES_PASSWORD=POSTGRES_HESLO

EMAIL_HOST=mail.vase-firma.cz
EMAIL_PORT=587
EMAIL_HOST_USER=helpdesk@vase-firma.cz
EMAIL_HOST_PASSWORD=heslo
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=helpdesk@vase-firma.cz
HELPDESK_EMAIL=helpdesk@vase-firma.cz

IMAP_HOST=mail.vase-firma.cz
IMAP_PORT=993
IMAP_USER=helpdesk@vase-firma.cz
IMAP_PASSWORD=heslo
```

### Spuštění

```bash
# Sestavení a spuštění
docker compose up --build -d

# Kontrola logů
docker compose logs -f

# Vytvoření superuživatele
docker compose exec web python manage.py createsuperuser

# Zastavení
docker compose down
```

### SSL certifikát (Let's Encrypt)

```bash
# 1. Vytvořte certifikát (doménu upravte v nginx/nginx.conf)
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d helpdesk.vase-domena.cz \
  --email vas@email.cz --agree-tos

# 2. Odkomentujte HTTPS blok v nginx/nginx.conf

# 3. Restartujte nginx
docker compose restart nginx
```

### Aktualizace

```bash
git pull
docker compose up --build -d
docker compose exec web python manage.py migrate
```

---

## Struktura projektu

```
├── helpdesk/               # Django projekt (nastavení, URL, Celery)
│   └── settings/
│       ├── base.py         # Společná konfigurace
│       ├── local.py        # Lokální vývoj (SQLite)
│       └── production.py   # Produkce (PostgreSQL)
├── apps/
│   ├── accounts/           # Uživatelé, firmy, role
│   ├── tickets/            # Tikety, komentáře, záznamy času
│   ├── notifications/      # SMTP notifikace + IMAP polling
│   └── stats/              # Měsíční statistiky
├── templates/              # HTML šablony (Tailwind CSS + HTMX)
├── locale/                 # Překlady (cs, en)
├── nginx/                  # Nginx konfigurace
├── Dockerfile
└── docker-compose.yml
```

---

## Licence

Interní projekt HCV. Všechna práva vyhrazena.
