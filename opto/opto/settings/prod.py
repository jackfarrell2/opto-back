from .base import *
import os

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ['apidfsopto.xyz', 'www.apidfsopto.xyz']
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

CORS_ALLOWED_ORIGINS = [
    'https://dfsopto.com',
    'https://www.dfsopto.com',
]

CSRF_TRUSTED_ORIGINS = ['https://*.apidfsopto.xyz']
