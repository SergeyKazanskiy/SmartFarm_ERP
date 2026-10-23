from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pm"
    label = "pm"
    verbose_name = _("PM — Project Management")

    def ready(self) -> None:
        from apps.pm import handlers  # noqa: F401