import os
from .base import *

# Production: ошибки не должны показываться посетителям
DEBUG = False

# Эти значения нужно задать на рабочем сервере
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')


# from .base import *  # noqa: F401, F403

# DEBUG = False

# # В продакшене Django не раздаёт статику сам — этим занимается nginx
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True