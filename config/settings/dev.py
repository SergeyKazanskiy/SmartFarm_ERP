from .base import *

# Режим разработки
DEBUG = True

# Пока работаем локально на своём Mac
ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# from .base import *  # noqa: F401, F403

# DEBUG = True

# # В dev-режиме удобно логировать SQL
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {"class": "logging.StreamHandler"},
#     },
#     "root": {
#         "handlers": ["console"],
#         "level": "INFO",
#     },
#     "loggers": {
#         "django.db.backends": {
#             "handlers": ["console"],
#             "level": "INFO",   # WARNING → INFO чтобы видеть SQL
#             "propagate": False,
#         },
#     },
# }