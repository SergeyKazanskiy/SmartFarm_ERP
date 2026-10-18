import os
from .base import *

# Production: ошибки не должны показываться посетителям
DEBUG = False

# Эти значения нужно задать на рабочем сервере
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')