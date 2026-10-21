"""
Утилиты для сервисов CP.
"""
import uuid

from django.db import transaction


def gen_code(prefix: str) -> str:
    """
    Генерирует человекочитаемый code вида `CONT-A1B2C3D4`.
    Используется, если code не передан явно.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def get_company_from_user(user) -> int:
    """Возвращает id текущей компании пользователя или бросает ошибку."""
    company_id = getattr(user, "current_company_id", None)
    if not company_id:
        raise ValueError("У пользователя не выбрана активная компания")
    return company_id