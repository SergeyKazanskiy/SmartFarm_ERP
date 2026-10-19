from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
    label = "tasks"
    verbose_name = _("Tasks & Workflow")

    def ready(self) -> None:
        # Регистрируем подписчиков Event Bus
        from apps.tasks import handlers  # noqa: F401