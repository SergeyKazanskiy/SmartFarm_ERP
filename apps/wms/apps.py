from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WMSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.wms"
    label = "wms"
    verbose_name = _("Warehouse Management")

    def ready(self) -> None:
        from apps.wms import handlers  # noqa: F401