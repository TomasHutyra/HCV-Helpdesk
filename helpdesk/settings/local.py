from .base import *  # noqa

DEBUG = True

# SQLite pro lokální vývoj
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# E-maily se zobrazují v konzoli (nevyžaduje SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery tasky běží synchronně — nevyžaduje Redis
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
