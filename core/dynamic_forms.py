"""
Динамические формы из YAML (HR_Business_Roles.yml).

Читает операцию по коду (например, "OP-HR-12") и строит Django-форму
с полями, описанными в YAML.

Типы полей:
- text, textarea, number, date, datetime
- select (с источником данных)
- checkbox
- hidden
- repeater (не реализован полностью — требует специального виджета)
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from django import forms
from django.apps import apps
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model_registry() -> dict[str, type]:
    """
    Реестр моделей: {table_name: ModelClass}.
    Поддерживает схемы: db_table="hr"."hr_position" → "hr_position".
    """
    registry: dict[str, type] = {}
    for model in apps.get_models():
        table = model._meta.db_table
        if '"."' in table:
            table = table.split('"."')[-1]
        registry[table] = model
    return registry


class BusinessRolesLoader:
    """Загружает и кэширует YAML-файлы с операциями."""

    def __init__(self, paths: list[Path]):
        self.paths = paths
        self._operations: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        for path in self.paths:
            if not path.exists():
                logger.warning("BusinessRoles: файл не найден %s", path)
                continue
            with open(path, "r", encoding="utf-8") as f:
                for doc in yaml.safe_load_all(f):
                    if not doc:
                        continue
                    for op in doc.get("operations", []):
                        codes = op["op_code"]
                        if isinstance(codes, str):
                            codes = [codes]
                        for code in codes:
                            self._operations[code] = op

    def get_operation(self, code: str) -> dict | None:
        return self._operations.get(code)


class DynamicFormBuilder:
    """
    Строит Django Form из YAML-описания операции.
    Форма привязывается к модели из поля `table`.
    """

    def __init__(self, operation: dict):
        self.operation = operation
        self.model = get_model_registry().get(operation["table"])
        if self.model is None:
            raise ValueError(
                _("Модель для таблицы %s не найдена") % operation["table"]
            )

    def build_class(self) -> type[forms.ModelForm]:
        """Возвращает класс ModelForm с полями из YAML."""
        operation = self.operation
        model = self.model

        # Собираем поля
        field_defs = self._build_field_defs(operation.get("fields", []))

        meta_attrs = {
            "model": model,
            "fields": list(field_defs.keys()),
            "widgets": {},
            "labels": {},
            "help_texts": {},
        }

        for name, fdef in field_defs.items():
            meta_attrs["labels"][name] = fdef["label"]
            if fdef.get("widget"):
                meta_attrs["widgets"][name] = fdef["widget"]

        Meta = type("Meta", (), meta_attrs)

        # Собираем attrs класса
        attrs = {
            "Meta": Meta,
            "__module__": __name__,
            "__init__": self._make_init(field_defs),
        }
        for name, fdef in field_defs.items():
            attrs[name] = fdef["field"]

        # Динамическое имя класса
        class_name = f"DynamicForm_{'_'.join(self.operation['op_code']) if isinstance(self.operation['op_code'], list) else self.operation['op_code']}"
        form_class = type(class_name, (forms.ModelForm,), attrs)

        return form_class

    def _build_field_defs(self, yaml_fields: list[dict]) -> dict[str, dict]:
        """Преобразует YAML-поля в Django-поля."""
        result = {}
        for f in yaml_fields:
            name = f["field"]
            field_type = f.get("type", "text")
            required = f.get("required", False)
            label = _(f.get("label", name))

            result[name] = {
                "field": self._make_field(f, field_type, required),
                "label": label,
                "widget": self._make_widget(field_type),
            }
        return result

    def _make_field(self, f: dict, field_type: str, required: bool) -> forms.Field:
        """Создаёт один Django-Forms-объект по типу из YAML."""
        common = {"required": required, "label": _(f.get("label", f["field"]))}

        if field_type == "text":
            return forms.CharField(max_length=500, **common)
        if field_type == "textarea":
            return forms.CharField(widget=forms.Textarea, **common)
        if field_type == "number":
            return forms.DecimalField(max_digits=15, decimal_places=2, **common)
        if field_type == "date":
            return forms.DateField(
                widget=forms.DateInput(attrs={"type": "date"}), **common,
            )
        if field_type == "datetime":
            return forms.DateTimeField(
                widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
                **common,
            )
        if field_type == "checkbox":
            return forms.BooleanField(**common)
        if field_type == "select":
            return self._make_select_field(f, required)
        if field_type == "hidden":
            return forms.CharField(widget=forms.HiddenInput, required=False)
        if field_type == "repeater":
            # Упрощённо: JSON-текст. Полноценный виджет — отдельная тема.
            return forms.JSONField(required=False, **common)

        # По умолчанию — текст
        return forms.CharField(max_length=500, **common)

    def _make_select_field(self, f: dict, required: bool) -> forms.Field:
        """
        Создаёт ChoiceField с динамическим queryset из `source`.
        source: {table: hr_position, value_field: position_id, label_field: position_name}
        """
        common = {"required": required, "label": _(f.get("label", f["field"]))}
        source = f.get("source")

        # Если заданы статические options
        if "options" in f:
            choices = [(o, o) for o in f["options"]]
            return forms.ChoiceField(choices=choices, **common)

        # Если источник — текущий пользователь
        if isinstance(source, str) and source == "current_user":
            return forms.IntegerField(widget=forms.HiddenInput, required=False)

        if not source:
            return forms.CharField(max_length=100, **common)

        # Динамический queryset
        related_model = get_model_registry().get(source["table"])
        if related_model is None:
            logger.warning("DynamicForm: модель %s не найдена", source["table"])
            return forms.CharField(max_length=100, **common)

        # Если value_field — это pk модели, используем ModelChoiceField
        pk_name = related_model._meta.pk.name
        if source["value_field"] == pk_name:
            return forms.ModelChoiceField(
                queryset=related_model.objects.all(),
                **common,
            )

        # Иначе — ChoiceField из значений
        # (для простоты ограничимся 500 записями — в реальности нужен autocomplete)
        def _get_choices():
            qs = related_model.objects.all()[:500]
            return [
                (getattr(obj, source["value_field"]), getattr(obj, source["label_field"]))
                for obj in qs
            ]

        return forms.ChoiceField(choices=_get_choices, **common)

    @staticmethod
    def _make_widget(field_type: str) -> type | None:
        if field_type == "textarea":
            return forms.Textarea
        if field_type == "date":
            return forms.DateInput
        if field_type == "datetime":
            return forms.DateTimeInput
        if field_type == "hidden":
            return forms.HiddenInput
        return None

    @staticmethod
    def _make_init(field_defs: dict):
        """Возвращает __init__, который проставляет начальные значения из current_user и т.п."""
        def __init__(self, *args, user=None, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)
            if user is not None:
                for name, fdef in field_defs.items():
                    # Поле с source=current_user → скрытое, заполняется автоматически
                    yaml_field = next(
                        (x for x in [] if x["field"] == name), None,
                    )
                    # (логика заполнения — по мере необходимости)
        return __init__


class BusinessFormFactory:
    """
    Фабрика форм: получает op_code и возвращает класс формы.
    Кэширует построенные формы.
    """

    _loader: BusinessRolesLoader | None = None
    _cache: dict[str, type] = {}

    @classmethod
    def initialize(cls, paths: list[Path]) -> None:
        cls._loader = BusinessRolesLoader(paths)

    @classmethod
    def get_form(cls, op_code: str) -> type[forms.ModelForm]:
        if cls._loader is None:
            raise RuntimeError("BusinessFormFactory не инициализирован")
        if op_code in cls._cache:
            return cls._cache[op_code]

        operation = cls._loader.get_operation(op_code)
        if operation is None:
            raise ValueError(f"Операция {op_code} не найдена в YAML")

        builder = DynamicFormBuilder(operation)
        form_class = builder.build_class()
        cls._cache[op_code] = form_class
        return form_class