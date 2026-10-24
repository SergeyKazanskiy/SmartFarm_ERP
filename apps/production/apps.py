from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProductionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.production"
    label = "production"
    verbose_name = _("Production")

    def ready(self) -> None:
        from apps.production import handlers  # noqa: F401