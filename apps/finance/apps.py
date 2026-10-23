from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = _("Finance & Treasury")

    def ready(self) -> None:
        from apps.finance import handlers  # noqa: F401