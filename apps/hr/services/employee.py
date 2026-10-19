"""
Сервисный слой HR: бизнес-операции из HR_Business_Roles.yml.
Каждый метод — одна бизнес-операция (OP-HR-XX), публикующая событие.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import HREvents as HR

from apps.hr.models import HREmployee


class EmployeeService:
    """
    Бизнес-операции над сотрудником.
    Все методы — @transaction.atomic: либо всё, либо ничего.
    """

    @staticmethod
    @transaction.atomic
    def hire(
        *,
        company_id: int,
        natural_person_id: int,
        position_id: int | None,
        department_id: int | None,
        employment_date,
        personnel_number: str = "",
        schedule_id: int | None = None,
        actor_user=None,
    ) -> HREmployee:
        """
        OP-HR-12: Приём сотрудника на работу.
        Создаёт HREmployee и публикует событие HR.employee.hire.
        """
        employee = HREmployee.objects.create(
            company_id=company_id,
            natural_person_id=natural_person_id,
            personnel_number=personnel_number,
            position_id=position_id,
            department_id=department_id,
            employment_date=employment_date,
            schedule_id=schedule_id,
            status="hired",
        )

        EventBus.publish(
            HR.EMPLOYEE_HIRE,
            company_id=company_id,
            payload={
                "employee_id": employee.id,
                "natural_person_id": natural_person_id,
                "position_id": position_id,
                "department_id": department_id,
                "employment_date": employment_date.isoformat(),
                "actor_user_id": getattr(actor_user, "id", None),
            },
        )
        return employee

    @staticmethod
    @transaction.atomic
    def transfer(
        *,
        employee_id: int,
        company_id: int,
        position_id: int,
        department_id: int,
        schedule_id: int | None,
        actor_user=None,
    ) -> HREmployee:
        """OP-HR-13: Кадровый перевод."""
        employee = HREmployee.objects.select_for_update().get(
            pk=employee_id, company_id=company_id,
        )
        old = {
            "position_id": employee.position_id,
            "department_id": employee.department_id,
            "schedule_id": employee.schedule_id,
        }
        employee.position_id = position_id
        employee.department_id = department_id
        employee.schedule_id = schedule_id
        employee.save(update_fields=[
            "position", "department_id", "schedule", "updated_at",
        ])

        EventBus.publish(
            HR.EMPLOYEE_TRANSFER,
            company_id=company_id,
            payload={
                "employee_id": employee.id,
                "old": old,
                "new": {
                    "position_id": position_id,
                    "department_id": department_id,
                    "schedule_id": schedule_id,
                },
                "actor_user_id": getattr(actor_user, "id", None),
            },
        )
        return employee

    @staticmethod
    @transaction.atomic
    def dismiss(
        *,
        employee_id: int,
        company_id: int,
        dismissal_date,
        actor_user=None,
    ) -> HREmployee:
        """OP-HR-17: Увольнение сотрудника."""
        employee = HREmployee.objects.select_for_update().get(
            pk=employee_id, company_id=company_id,
        )
        if employee.status not in ("active", "on_leave", "suspended"):
            raise ValueError(_("Employee cannot be dismissed from status %s") % employee.status)

        employee.status = "dismissed"
        employee.dismissal_date = dismissal_date
        employee.save(update_fields=["status", "dismissal_date", "updated_at"])

        EventBus.publish(
            HR.EMPLOYEE_DISMISS,
            company_id=company_id,
            payload={
                "employee_id": employee.id,
                "dismissal_date": dismissal_date.isoformat(),
                "actor_user_id": getattr(actor_user, "id", None),
            },
        )
        return employee