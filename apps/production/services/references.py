"""
Мастер-данные: технологии, центры, маршруты, операции, контрольные точки.
OP-PROD-01…14.
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import ProductionEvents as PRE

from apps.production.models import (
    OperationDefinition, QualityPoint, Routing, Technology, WorkCenter,
)
from apps.production.services.helpers import gen_code, validate_json_list


class TechnologyService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-01."""
        t = Technology.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("TECH"),
            name=data["name"],
        )
        EventBus.publish(
            PRE.TECHNOLOGY_CREATE,
            company_id=company_id,
            payload={"technology_id": t.id, "name": t.name},
        )
        return t

    @staticmethod
    @transaction.atomic
    def rename(*, company_id: int, technology_id: int, new_name: str):
        """OP-PROD-02."""
        t = Technology.objects.select_for_update().get(
            pk=technology_id, company_id=company_id,
        )
        t.name = new_name
        t.save(update_fields=["name", "updated_at"])
        EventBus.publish(
            PRE.TECHNOLOGY_RENAME,
            company_id=company_id,
            payload={"technology_id": t.id, "new_name": new_name},
        )
        return t


class WorkCenterService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-05."""
        wc = WorkCenter.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("WC"),
            name=data["name"],
        )
        EventBus.publish(
            PRE.WORK_CENTER_CREATE,
            company_id=company_id,
            payload={"work_center_id": wc.id, "name": wc.name},
        )
        return wc

    @staticmethod
    @transaction.atomic
    def rename(*, company_id: int, work_center_id: int, new_name: str):
        """OP-PROD-06."""
        wc = WorkCenter.objects.select_for_update().get(
            pk=work_center_id, company_id=company_id,
        )
        wc.name = new_name
        wc.save(update_fields=["name", "updated_at"])
        EventBus.publish(
            PRE.WORK_CENTER_RENAME,
            company_id=company_id,
            payload={"work_center_id": wc.id},
        )
        return wc


class RoutingService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-03."""
        r = Routing.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("ROUT"),
            technology_id=data.get("technology_id"),
            name=data["name"],
        )
        EventBus.publish(
            PRE.ROUTING_CREATE,
            company_id=company_id,
            payload={"routing_id": r.id, "name": r.name},
        )
        return r

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, routing_id: int, data: dict):
        """OP-PROD-04."""
        r = Routing.objects.select_for_update().get(
            pk=routing_id, company_id=company_id,
        )
        for field in ("name", "technology_id"):
            if field in data:
                setattr(r, field, data[field])
        r.save()
        EventBus.publish(
            PRE.ROUTING_UPDATE,
            company_id=company_id,
            payload={"routing_id": r.id},
        )
        return r


class OperationService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-07."""
        op = OperationDefinition.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("OPDEF"),
            routing_id=data["routing_id"],
            name=data["name"],
            sequence_no=data["sequence_no"],
            work_center_id=data.get("work_center_id"),
            resources_json=validate_json_list(
                data.get("resources_json"), "resources_json",
            ),
            parameters_json=validate_json_list(
                data.get("parameters_json"), "parameters_json",
            ),
        )
        EventBus.publish(
            PRE.OPERATION_CREATE,
            company_id=company_id,
            payload={
                "operation_id": op.id,
                "routing_id": op.routing_id,
                "sequence_no": op.sequence_no,
            },
        )
        return op

    @staticmethod
    @transaction.atomic
    def update_parameters(*, company_id: int, operation_id: int, parameters_json: list):
        """OP-PROD-08."""
        op = OperationDefinition.objects.select_for_update().get(
            pk=operation_id, company_id=company_id,
        )
        op.parameters_json = validate_json_list(parameters_json, "parameters_json")
        op.save(update_fields=["parameters_json", "updated_at"])
        EventBus.publish(
            PRE.OPERATION_UPDATE_PARAMETERS,
            company_id=company_id,
            payload={"operation_id": op.id},
        )
        return op

    @staticmethod
    @transaction.atomic
    def update_resources(*, company_id: int, operation_id: int, resources_json: list):
        """OP-PROD-09."""
        op = OperationDefinition.objects.select_for_update().get(
            pk=operation_id, company_id=company_id,
        )
        op.resources_json = validate_json_list(resources_json, "resources_json")
        op.save(update_fields=["resources_json", "updated_at"])
        EventBus.publish(
            PRE.OPERATION_UPDATE_RESOURCES,
            company_id=company_id,
            payload={"operation_id": op.id},
        )
        return op

    @staticmethod
    @transaction.atomic
    def move_work_center(*, company_id: int, operation_id: int, work_center_id: int):
        """OP-PROD-10."""
        op = OperationDefinition.objects.select_for_update().get(
            pk=operation_id, company_id=company_id,
        )
        op.work_center_id = work_center_id
        op.save(update_fields=["work_center", "updated_at"])
        EventBus.publish(
            PRE.OPERATION_MOVE_WORK_CENTER,
            company_id=company_id,
            payload={"operation_id": op.id, "work_center_id": work_center_id},
        )
        return op

    @staticmethod
    @transaction.atomic
    def reorder(*, company_id: int, operation_id: int, sequence_no: int):
        """OP-PROD-11."""
        op = OperationDefinition.objects.select_for_update().get(
            pk=operation_id, company_id=company_id,
        )
        op.sequence_no = sequence_no
        op.save(update_fields=["sequence_no", "updated_at"])
        EventBus.publish(
            PRE.OPERATION_REORDER,
            company_id=company_id,
            payload={"operation_id": op.id, "sequence_no": sequence_no},
        )
        return op

    @staticmethod
    @transaction.atomic
    def rename(*, company_id: int, operation_id: int, new_name: str):
        """OP-PROD-12."""
        op = OperationDefinition.objects.select_for_update().get(
            pk=operation_id, company_id=company_id,
        )
        op.name = new_name
        op.save(update_fields=["name", "updated_at"])
        EventBus.publish(
            PRE.OPERATION_RENAME,
            company_id=company_id,
            payload={"operation_id": op.id},
        )
        return op


class QualityPointService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-13."""
        qp = QualityPoint.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("QP"),
            operation_id=data["operation_id"],
            name=data["name"],
        )
        EventBus.publish(
            PRE.QUALITY_POINT_CREATE,
            company_id=company_id,
            payload={"quality_point_id": qp.id, "operation_id": qp.operation_id},
        )
        return qp

    @staticmethod
    @transaction.atomic
    def rename(*, company_id: int, quality_point_id: int, new_name: str):
        """OP-PROD-14."""
        qp = QualityPoint.objects.select_for_update().get(
            pk=quality_point_id, company_id=company_id,
        )
        qp.name = new_name
        qp.save(update_fields=["name", "updated_at"])
        EventBus.publish(
            PRE.QUALITY_POINT_RENAME,
            company_id=company_id,
            payload={"quality_point_id": qp.id},
        )
        return qp