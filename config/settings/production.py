from .base import *
from django.core.exceptions import ImproperlyConfigured

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('development-') or 'change-me' in SECRET_KEY:
    raise ImproperlyConfigured('Set a random DJANGO_SECRET_KEY of at least 50 characters.')
if not SITE_URL.startswith('https://') or not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('Set HTTPS SITE_URL and CSRF_TRUSTED_ORIGINS.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Production requires PostgreSQL.')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Only enable this behind a proxy that strips client-provided forwarded headers.
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
