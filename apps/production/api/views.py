"""
DRF ViewSets Production.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.production.api.serializers import (
    BomItemSerializer, BomSerializer, MaterialPriceHistorySerializer,
    OperationDefinitionSerializer, OperationExecutionSerializer,
    ProductionOrderSerializer, QualityPointSerializer,
    RoutingSerializer, TechnologySerializer,
    WorkCenterSerializer, WorkOrderSerializer,
)
from apps.production.models import (
    Bom, BomItem, MaterialPriceHistory, OperationDefinition,
    OperationExecution, ProductionOrder, QualityPoint,
    Routing, Technology, WorkCenter, WorkOrder,
)
from apps.production.services import (
    BomItemService, BomService, MaterialPriceHistoryService,
    OperationExecutionService, OperationService,
    ProductionOrderService, QualityPointService,
    RoutingService, TechnologyService,
    WorkCenterService, WorkOrderService,
)


class CompanyScopedMixin:
    def get_company_id(self) -> int:
        cid = getattr(self.request.user, "current_company_id", None)
        if not cid:
            raise PermissionDenied("Компания не выбрана")
        return cid

    def get_employee_id(self) -> int | None:
        return getattr(self.request.user, "hr_employee_id", None)


# --- Мастер-данные ---

class TechnologyViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TechnologySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Technology.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = TechnologyService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class WorkCenterViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WorkCenterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkCenter.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = WorkCenterService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class RoutingViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = RoutingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Routing.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = RoutingService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class OperationDefinitionViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = OperationDefinitionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OperationDefinition.objects.filter(company_id=self.get_company_id())
        r = self.request.query_params.get("routing_id")
        if r:
            qs = qs.filter(routing_id=r)
        return qs.order_by("routing", "sequence_no")

    def perform_create(self, serializer):
        serializer.instance = OperationService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class QualityPointViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = QualityPointSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QualityPoint.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = QualityPointService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# --- BOM ---

class BomViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bom.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("items")

    def perform_create(self, serializer):
        serializer.instance = BomService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = BomService.update(
            company_id=self.get_company_id(),
            bom_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )


class BomItemViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BomItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = BomItem.objects.filter(company_id=self.get_company_id())
        b = self.request.query_params.get("bom_id")
        if b:
            qs = qs.filter(bom_id=b)
        return qs

    def perform_create(self, serializer):
        serializer.instance = BomItemService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"], url_path="update-quantity")
    def update_quantity(self, request, pk=None):
        item = self.get_object()
        val = request.data.get("quantity")
        if val is None:
            raise ValidationError("quantity обязателен")
        item = BomItemService.update_quantity(
            company_id=self.get_company_id(),
            bom_item_id=item.id, quantity=val,
        )
        return Response(BomItemSerializer(item).data)

    @action(detail=True, methods=["post"], url_path="replace-material")
    def replace_material(self, request, pk=None):
        item = self.get_object()
        mid = request.data.get("material_id")
        if mid is None:
            raise ValidationError("material_id обязателен")
        item = BomItemService.replace_material(
            company_id=self.get_company_id(),
            bom_item_id=item.id, material_id=int(mid),
        )
        return Response(BomItemSerializer(item).data)

    @action(detail=True, methods=["post"], url_path="update-cost")
    def update_cost(self, request, pk=None):
        item = self.get_object()
        val = request.data.get("unit_cost")
        if val is None:
            raise ValidationError("unit_cost обязателен")
        item = BomItemService.update_cost(
            company_id=self.get_company_id(),
            bom_item_id=item.id, unit_cost=val,
            actor_employee_id=self.get_employee_id(),
        )
        return Response(BomItemSerializer(item).data)


class MaterialPriceHistoryViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MaterialPriceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialPriceHistory.objects.filter(company_id=self.get_company_id())
        m = self.request.query_params.get("material_id")
        if m:
            qs = qs.filter(material_id=m)
        return qs.order_by("-effective_date")

    def perform_create(self, serializer):
        serializer.instance = MaterialPriceHistoryService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )


# --- Production Orders ---

class ProductionOrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProductionOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ProductionOrder.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("bom", "routing")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-planned_start_date")

    def perform_create(self, serializer):
        serializer.instance = ProductionOrderService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        try:
            order = ProductionOrderService.confirm(
                company_id=self.get_company_id(),
                production_order_id=order.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProductionOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="update-plan")
    def update_plan(self, request, pk=None):
        order = self.get_object()
        try:
            order = ProductionOrderService.update_plan(
                company_id=self.get_company_id(),
                production_order_id=order.id,
                data=dict(request.data),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProductionOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        try:
            order = ProductionOrderService.complete(
                company_id=self.get_company_id(),
                production_order_id=order.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProductionOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get("reason", "")
        try:
            order = ProductionOrderService.cancel(
                company_id=self.get_company_id(),
                production_order_id=order.id, reason=reason,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProductionOrderSerializer(order).data)


# --- Work Orders ---

class WorkOrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WorkOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkOrder.objects.filter(company_id=self.get_company_id())
        po = self.request.query_params.get("production_order_id")
        if po:
            qs = qs.filter(production_order_id=po)
        return qs.order_by("-planned_start")

    def perform_create(self, serializer):
        serializer.instance = WorkOrderService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        wo = self.get_object()
        try:
            wo = WorkOrderService.start(
                company_id=self.get_company_id(), work_order_id=wo.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        wo = self.get_object()
        reason = request.data.get("reason", "")
        try:
            wo = WorkOrderService.hold(
                company_id=self.get_company_id(),
                work_order_id=wo.id, reason=reason,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        wo = self.get_object()
        try:
            wo = WorkOrderService.resume(
                company_id=self.get_company_id(), work_order_id=wo.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        wo = self.get_object()
        try:
            wo = WorkOrderService.complete(
                company_id=self.get_company_id(), work_order_id=wo.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WorkOrderSerializer(wo).data)

    @action(detail=True, methods=["post"], url_path="register-materials")
    def register_materials(self, request, pk=None):
        wo = self.get_object()
        payload = request.data.get("actual_materials_json", [])
        wo = WorkOrderService.register_materials(
            company_id=self.get_company_id(),
            work_order_id=wo.id, actual_materials_json=payload,
        )
        return Response(WorkOrderSerializer(wo).data)


# --- Operation Executions ---

class OperationExecutionViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = OperationExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OperationExecution.objects.filter(company_id=self.get_company_id())
        wo = self.request.query_params.get("work_order_id")
        if wo:
            qs = qs.filter(work_order_id=wo)
        return qs.order_by("-start_time")

    def perform_create(self, serializer):
        serializer.instance = OperationExecutionService.start(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"], url_path="assign-employee")
    def assign_employee(self, request, pk=None):
        ex = self.get_object()
        eid = request.data.get("employee_id")
        if eid is None:
            raise ValidationError("employee_id обязателен")
        ex = OperationExecutionService.assign_employee(
            company_id=self.get_company_id(),
            execution_id=ex.id, employee_id=int(eid),
        )
        return Response(OperationExecutionSerializer(ex).data)

    @action(detail=True, methods=["post"], url_path="record-measurements")
    def record_measurements(self, request, pk=None):
        ex = self.get_object()
        payload = request.data.get("measurements_json", [])
        ex = OperationExecutionService.record_measurements(
            company_id=self.get_company_id(),
            execution_id=ex.id, measurements_json=payload,
        )
        return Response(OperationExecutionSerializer(ex).data)

    @action(detail=True, methods=["post"], url_path="record-quality")
    def record_quality(self, request, pk=None):
        ex = self.get_object()
        payload = request.data.get("quality_results_json", [])
        ex = OperationExecutionService.record_quality(
            company_id=self.get_company_id(),
            execution_id=ex.id, quality_results_json=payload,
        )
        return Response(OperationExecutionSerializer(ex).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        ex = self.get_object()
        try:
            ex = OperationExecutionService.complete(
                company_id=self.get_company_id(), execution_id=ex.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OperationExecutionSerializer(ex).data)

    @action(detail=True, methods=["post"], url_path="send-to-rework")
    def send_to_rework(self, request, pk=None):
        ex = self.get_object()
        reason = request.data.get("reason", "")
        try:
            ex = OperationExecutionService.send_to_rework(
                company_id=self.get_company_id(),
                execution_id=ex.id, reason=reason,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OperationExecutionSerializer(ex).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        ex = self.get_object()
        try:
            ex = OperationExecutionService.cancel(
                company_id=self.get_company_id(), execution_id=ex.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OperationExecutionSerializer(ex).data)