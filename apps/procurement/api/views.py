"""
DRF ViewSets Procurement. Все запросы фильтруются по компании пользователя.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.procurement.api.serializers import (
    DeliverySerializer, OrderCreateSerializer, OrderDetailSerializer,
    OrderHistorySerializer, OrderLineSerializer, OrderListSerializer,
    RequisitionCreateSerializer, RequisitionDetailSerializer,
    RequisitionLineSerializer, RequisitionListSerializer,
    RFQCreateSerializer, RFQDetailSerializer, RFQListSerializer,
    RFQSupplierSerializer, SupplierQuoteSerializer, SupplierSerializer,
)
from apps.procurement.models import (
    Delivery, Order, OrderHistory, OrderLine, Requisition,
    RequisitionLine, RFQ, RFQSupplier, Supplier, SupplierQuote,
)
from apps.procurement.services import (
    DeliveryService, OrderLineService, OrderService,
    RequisitionLineService, RequisitionService,
    RFQService, RFQSupplierService, SupplierQuoteService, SupplierService,
)


class CompanyScopedMixin:
    def get_company_id(self) -> int:
        cid = getattr(self.request.user, "current_company_id", None)
        if not cid:
            raise PermissionDenied("Компания не выбрана")
        return cid

    def get_employee_id(self) -> int | None:
        return getattr(self.request.user, "hr_employee_id", None)


# ============================================================
# Поставщики
# ============================================================

class SupplierViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Supplier.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            if self.request.query_params.get("preferred") == "true":
                qs = qs.filter(is_preferred=True)
        return qs.order_by("-is_preferred", "-rating")

    def perform_create(self, serializer):
        serializer.instance = SupplierService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = SupplierService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


# ============================================================
# Заявки
# ============================================================

class RequisitionViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Requisition.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-requisition_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RequisitionDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return RequisitionCreateSerializer
        return RequisitionListSerializer

    def perform_create(self, serializer):
        serializer.instance = RequisitionService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        req = self.get_object()
        req = RequisitionService.submit(
            company_id=self.get_company_id(), requisition_id=req.id,
        )
        return Response(RequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        try:
            req = RequisitionService.review(
                company_id=self.get_company_id(),
                requisition_id=req.id, new_status="approved",
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RequisitionDetailSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        try:
            req = RequisitionService.review(
                company_id=self.get_company_id(),
                requisition_id=req.id, new_status="rejected",
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RequisitionDetailSerializer(req).data)


class RequisitionLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = RequisitionLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RequisitionLine.objects.filter(company_id=self.get_company_id())
        r = self.request.query_params.get("requisition_id")
        if r:
            qs = qs.filter(requisition_id=r)
        return qs

    def perform_create(self, serializer):
        serializer.instance = RequisitionLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = RequisitionLineService.update(
            company_id=self.get_company_id(),
            line_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )


# ============================================================
# RFQ
# ============================================================

class RFQViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RFQ.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("suppliers")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-rfq_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RFQDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return RFQCreateSerializer
        return RFQListSerializer

    def perform_create(self, serializer):
        serializer.instance = RFQService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        rfq = self.get_object()
        try:
            rfq = RFQService.send(
                company_id=self.get_company_id(), rfq_id=rfq.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RFQDetailSerializer(rfq).data)

    @action(detail=True, methods=["post"], url_path="mark-responded")
    def mark_responded(self, request, pk=None):
        rfq = self.get_object()
        try:
            rfq = RFQService.mark_responded(
                company_id=self.get_company_id(), rfq_id=rfq.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RFQDetailSerializer(rfq).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        rfq = self.get_object()
        try:
            rfq = RFQService.close(
                company_id=self.get_company_id(), rfq_id=rfq.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(RFQDetailSerializer(rfq).data)


class RFQSupplierViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = RFQSupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = RFQSupplier.objects.filter(company_id=self.get_company_id())
        r = self.request.query_params.get("rfq_id")
        if r:
            qs = qs.filter(rfq_id=r)
        return qs

    def perform_create(self, serializer):
        serializer.instance = RFQSupplierService.add(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class SupplierQuoteViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = SupplierQuoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupplierQuote.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = SupplierQuoteService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Заказы
# ============================================================

class OrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Order.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines", "history").select_related("supplier")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
            sup = self.request.query_params.get("supplier_id")
            if sup:
                qs = qs.filter(supplier_id=sup)
        return qs.order_by("-order_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return OrderCreateSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        serializer.instance = OrderService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        order = self.get_object()
        try:
            order = OrderService.send(
                company_id=self.get_company_id(), order_id=order.id,
                actor_employee_id=self.get_employee_id(),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        try:
            order = OrderService.confirm(
                company_id=self.get_company_id(), order_id=order.id,
                actor_employee_id=self.get_employee_id(),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order = OrderService.cancel(
                company_id=self.get_company_id(), order_id=order.id,
                actor_employee_id=self.get_employee_id(),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(order).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """
        Принять поставку по конкретной позиции.
        Тело: {order_line_id, received_quantity, delivery_date}
        """
        order = self.get_object()
        line_id = request.data.get("order_line_id")
        qty = request.data.get("received_quantity")
        date = request.data.get("delivery_date")
        if not line_id or qty is None or not date:
            raise ValidationError(
                "order_line_id, received_quantity, delivery_date обязательны"
            )
        try:
            order = OrderService.receive(
                company_id=self.get_company_id(),
                order_id=order.id,
                order_line_id=int(line_id),
                received_quantity=qty,
                delivery_date=date,
                actor_employee_id=self.get_employee_id(),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(order).data)


class OrderLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = OrderLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OrderLine.objects.filter(company_id=self.get_company_id())
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        return qs

    def perform_create(self, serializer):
        serializer.instance = OrderLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = OrderLineService.update(
            company_id=self.get_company_id(),
            line_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )


class OrderHistoryViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OrderHistory.objects.filter(company_id=self.get_company_id())
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        return qs.order_by("-changed_at")


class DeliveryViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Delivery.objects.filter(company_id=self.get_company_id())
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        return qs.order_by("-delivery_date")

    def perform_create(self, serializer):
        serializer.instance = DeliveryService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )