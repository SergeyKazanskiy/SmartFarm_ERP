"""
Модели компаний (мультитенантность) и пользователей системы.
Обе таблицы — в схеме public.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """
    Компания (тенант). Все бизнес-данные ERP принадлежат компании.
    """
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name=_("Code"),
        help_text=_("Внутренний код компании, например COMP-001"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    short_name = models.CharField(
        max_length=100, blank=True, verbose_name=_("Short name")
    )
    tax_id = models.CharField(
        max_length=50, blank=True, db_index=True, verbose_name=_("Tax ID")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Кастомная модель пользователя.
    Пользователь привязан к одной или нескольким компаниям (M2M).
    Логин — по email.
    """
    email = models.EmailField(unique=True, verbose_name=_("Email"))
    full_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Full name")
    )
    companies = models.ManyToManyField(
        Company,
        related_name="users",
        blank=True,
        verbose_name=_("Companies"),
    )
    current_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_users",
        verbose_name=_("Current company"),
    )
    # Связь с сотрудником HR-модуля (employee_id в схеме hr),
    # нужна для self-service сценариев в мобильном приложении.
    # Используем не FK, а отдельное поле, чтобы избежать циклической зависимости.
    hr_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("HR employee ID"),
    )
    preferred_language = models.CharField(
        max_length=5,
        choices=[("ru", "Русский"), ("en", "English")],
        default="ru",
        verbose_name=_("Preferred language"),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.email