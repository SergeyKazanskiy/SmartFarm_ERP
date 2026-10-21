from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CPConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cp"
    label = "cp"
    verbose_name = _("Counterparties")

    def ready(self) -> None:
        from apps.cp import handlers  # noqa: F401