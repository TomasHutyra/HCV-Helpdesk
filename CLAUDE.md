# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Instalace závislostí
pip install -r requirements.txt

# Migrace databáze (první spuštění a po změně modelů)
python manage.py makemigrations
python manage.py migrate

# Vytvoření superuživatele
python manage.py createsuperuser

# Spuštění vývojového serveru
python manage.py runserver

# Překlady — generovat .po soubory ze zdrojového kódu
python manage.py makemessages -l cs -l en
# Překlady — zkompilovat .po → .mo
python manage.py compilemessages

# Testy (zatím žádné, spustí se jako: pytest nebo python manage.py test)
python manage.py test

# Produkce — Docker
docker compose up --build -d
docker compose logs -f
docker compose exec web python manage.py createsuperuser
```

`DJANGO_SETTINGS_MODULE` se přepíná v `.env`:
- Lokální vývoj: `helpdesk.settings.local` (SQLite, konzolový e-mail, Celery eager)
- Produkce: `helpdesk.settings.production` (PostgreSQL, SMTP, Redis+Celery)

## Project Overview

**HCV Helpdesk** — a ticket/request management system for HCV, which manages IT infrastructure and the Helios information system for client companies. The full specification is in `HCV_Helpdesk.md` (Czech).

This repository currently contains only the specification. No tech stack has been chosen yet.

## Domain Model

### Roles (a user may hold multiple roles)

| Role | Key permissions |
|------|----------------|
| **Žadatel** (Requester) | Creates tickets; sees only own tickets; can comment own tickets; cannot see resolution time; belongs to a company |
| **Řešitel** (Resolver) | Sees assigned tickets; comments; changes type/priority/area/status; logs time; resolves (requires resolution notes + time) |
| **Obchodník** (Sales) | Same as Resolver, but assignable only to "Požadavek na vývoj" (Development Request) type tickets |
| **Správce** (Manager) | Sees all tickets; assigns resolver/sales; resolves/rejects; sees all statistics |
| **Administrátor** (Admin) | Creates users; assigns roles; creates companies; assigns requesters to companies |

### Ticket Types & State Machines

**Hlášení problému** (Problem Report) — non-billable:
- States: `Nový → Řeší se → Vyřešeno`, any state `→ Zamítnuto`
- Assign resolver: `Nový → Řeší se`

**Požadavek na vývoj** (Development Request) — billable, may have a Sales person:
- States: `Nový → Příprava nabídky → Řeší se → Vyřešeno`, any state `→ Zamítnuto`
- Assign sales: `Nový → Příprava nabídky`
- Assign resolver: `Nový` or `Příprava nabídky → Řeší se`

**Námět na zlepšení** (Improvement Idea) — must be converted to another type before it can be resolved:
- States: `Nový`, any state `→ Zamítnuto`
- Cannot be resolved until type is changed

**Type change rules:** Ticket stays in its current state after a type change; if the new type doesn't have that state, reset to `Nový`.

**Locked states:** `Vyřešeno` and `Zamítnuto` are read-only except for moving back to `Řeší se` or `Příprava nabídky`.

**Resolution** requires: resolution notes + time spent. **Rejection** requires: rejection reason.

### Ticket Fields (requester must fill on creation)
- Type, Name, Description, Area (`IT` / `Helios` / `Neznámá`), Priority (`Vysoká` / `Střední` / `Nízká`)

### Email-to-ticket (inbound email)
Emails to a predefined address auto-create tickets with: type=`Hlášení problému`, name=subject, description=body, area=`Neznámá`, priority=`Střední`.

### Notifications (email)
| Event | Recipients | Content |
|-------|-----------|---------|
| New ticket created | Requester + all Managers | Type, Name, Description, Area, Priority |
| Status → `Řeší se` or `Příprava nabídky` | Requester | Name, new status |
| New comment added | All assigned parties (requester, resolver, sales) except commenter | Name, comment text |
| Ticket resolved or rejected | Requester | Name, new status, resolution notes or rejection reason |

### Statistics
- **Resolver view** (own, monthly): tickets resolved, assigned, avg resolution time, total time spent, counts per status
- **Manager view** (all, monthly): per-resolver stats + per-company stats (ticket count, open count, total time); can browse past months
