from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HRConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.hr"
    label = "hr"
    verbose_name = _("HR & Personnel")

    def ready(self) -> None:
        """
        Регистрируем подписчиков Event Bus.
        Импорт обязателен, чтобы декораторы @EventBus.subscribe сработали.
        """
        from apps.hr import handlers  # noqa: F401