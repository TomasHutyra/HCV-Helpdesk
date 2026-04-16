#!/bin/sh
set -e

echo "Čekám na databázi..."
python -c "
import time, psycopg2, os
from urllib.parse import urlparse
url = urlparse(os.environ.get('DATABASE_URL', ''))
for i in range(30):
    try:
        psycopg2.connect(
            host=url.hostname, port=url.port or 5432,
            user=url.username, password=url.password,
            dbname=url.path.lstrip('/')
        )
        break
    except Exception:
        time.sleep(2)
"

echo "Migrace..."
python manage.py migrate --settings=helpdesk.settings.production

echo "Sbírám statické soubory..."
python manage.py collectstatic --noinput --settings=helpdesk.settings.production

echo "Spouštím $@..."
exec "$@"
