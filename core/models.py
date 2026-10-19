"""
Базовые абстрактные модели, от которых наследуются все таблицы ERP.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    Добавляет created_at / updated_at.
    Использует auto_now_add / auto_now — не нужно переопределять save().
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("Created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )

    class Meta:
        abstract = True


class CompanyScopedModel(TimeStampedModel):
    """
    Абстрактная модель для мультитенантности.
    Каждая таблица ERP получает company_id и составной индекс.
    company_id — обычный FK на public.companies (без схем).
    """
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
        verbose_name=_("Company"),
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["company", "created_at"]),
        ]


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet с методами мягкого удаления."""

    def delete(self):
        return super().update(is_deleted=True)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Менеджер, который по умолчанию скрывает удалённые записи."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Мягкое удаление. Полезно для сущностей, которые нельзя физически терять
    (сотрудник, документ). По умолчанию queryset фильтрует is_deleted=False.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()   # доступ к удалённым: Model.all_objects.all()

    class Meta:
        abstract = True