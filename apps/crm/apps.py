from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CRMConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    label = "crm"
    verbose_name = _("CRM — Sales & Contracts")

    def ready(self) -> None:
        from apps.crm import handlers  # noqa: F401