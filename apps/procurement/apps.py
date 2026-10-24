from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProcurementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.procurement"
    label = "procurement"
    verbose_name = _("Procurement & Supply")

    def ready(self) -> None:
        from apps.procurement import handlers  # noqa: F401