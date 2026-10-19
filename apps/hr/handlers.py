"""
Подписчики HR-модуля на события других модулей.
На этом этапе — заглушки. Реальная логика появится, когда будут готовы
модули FIN, PROD, WMS и т.д.

Пример будущего подписчика:

    @EventBus.subscribe("TASK.task.complete")
    def on_task_complete(event):
        # Например, пересчитать actual_hours у сотрудника
        ...
"""
from core.event_bus import EventBus  # noqa: F401

# Здесь будут регистрироваться подписчики через @EventBus.subscribe(...)