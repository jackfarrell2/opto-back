from .base import *
from pathlib import Path
import os
import sys
PASS_BASE_DIR = Path(__file__).resolve().parent.parent
PASS_PARENT_DIR = PASS_BASE_DIR.parent.parent
sys.path.append(str(PASS_PARENT_DIR))
import db_info  # noqa

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ['apidfsopto.xyz', 'www.apidfsopto.xyz']
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

CORS_ALLOWED_ORIGINS = [
    'https://dfsopto.com',
    'https://www.dfsopto.com',
]

CSRF_TRUSTED_ORIGINS = ['https://*.apidfsopto.xyz']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_info.DB_NAME,
        'USER': db_info.DB_USER,
        'PASSWORD': db_info.DB_PASS,
        'HOST': db_info.DB_HOST,
        'PORT': db_info.DB_PORT,
    }
}
