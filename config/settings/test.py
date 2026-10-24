from .base import *
import os
DATABASES = {'default': dj_database_url.parse(os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:'))}
DATABASES['default']['CONN_MAX_AGE'] = 0
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
STORAGES['staticfiles'] = {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
MEDIA_ROOT = BASE_DIR / '.test-media'
