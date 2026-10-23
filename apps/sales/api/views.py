"""
DRF ViewSets Sales. Все запросы фильтруются по активной компании пользователя.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.sales.api.serializers import (
    CustomerSerializer, InvoiceSerializer, OpportunitySerializer,
    OrderDetailSerializer, OrderLineSerializer, OrderListSerializer,
    PriceListLineSerializer, PriceListSerializer,
    QuoteDetailSerializer, QuoteLineSerializer, QuoteListSerializer,
    ReturnLineSerializer, ReturnSerializer,
    ShipmentLineSerializer, ShipmentSerializer,
)
from apps.sales.models import (
    Customer, Invoice, Opportunity, Order, OrderLine,
    PriceList, PriceListLine, Quote, QuoteLine,
    Return, ReturnLine, Shipment, ShipmentLine,
)
from apps.sales.services import (
    CustomerService, InvoiceService, OpportunityService,
    OrderLineService, OrderService,
    PriceListLineService, PriceListService,
    QuoteLineService, QuoteService,
    ReturnLineService, ReturnService,
    ShipmentLineService, ShipmentService,
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
# Клиенты и прайс-листы
# ============================================================

class CustomerViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Customer.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            if self.request.query_params.get("active") == "true":
                qs = qs.filter(is_active=True)
            cat = self.request.query_params.get("category")
            if cat:
                qs = qs.filter(category=cat)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.instance = CustomerService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = CustomerService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


class PriceListViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceList.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")

    def perform_create(self, serializer):
        serializer.instance = PriceListService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = PriceListService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


class PriceListLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PriceListLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PriceListLine.objects.filter(company_id=self.get_company_id())
        pl = self.request.query_params.get("price_list_id")
        if pl:
            qs = qs.filter(price_list_id=pl)
        return qs

    def perform_create(self, serializer):
        serializer.instance = PriceListLineService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = PriceListLineService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


# ============================================================
# Воронка продаж
# ============================================================

class OpportunityViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Opportunity.objects.filter(company_id=self.get_company_id())
        st = self.request.query_params.get("stage")
        if st:
            qs = qs.filter(stage=st)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.instance = OpportunityService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"], url_path="update-stage")
    def update_stage(self, request, pk=None):
        opp = self.get_object()
        new_stage = request.data.get("stage")
        if not new_stage:
            raise ValidationError("stage обязателен")
        try:
            opp = OpportunityService.update_stage(
                company_id=self.get_company_id(),
                opportunity_id=opp.id, new_stage=new_stage,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OpportunitySerializer(opp).data)


# ============================================================
# КП
# ============================================================

class QuoteViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Quote.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-quote_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuoteDetailSerializer
        return QuoteListSerializer

    def perform_create(self, serializer):
        serializer.instance = QuoteService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        q = self.get_object()
        try:
            q = QuoteService.send(
                company_id=self.get_company_id(), quote_id=q.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(QuoteDetailSerializer(q).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        q = self.get_object()
        try:
            q = QuoteService.accept(
                company_id=self.get_company_id(), quote_id=q.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(QuoteDetailSerializer(q).data)


class QuoteLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = QuoteLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = QuoteLine.objects.filter(company_id=self.get_company_id())
        q = self.request.query_params.get("quote_id")
        if q:
            qs = qs.filter(quote_id=q)
        return qs

    def perform_create(self, serializer):
        serializer.instance = QuoteLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        QuoteLineService.delete(
            company_id=self.get_company_id(), line_id=instance.id,
        )


# ============================================================
# Заказы
# ============================================================

class OrderViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Order.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
            c = self.request.query_params.get("customer_id")
            if c:
                qs = qs.filter(customer_id=c)
        return qs.order_by("-order_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        serializer.instance = OrderService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        o = self.get_object()
        try:
            o = OrderService.confirm(
                company_id=self.get_company_id(), order_id=o.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(o).data)

    @action(detail=True, methods=["post"])
    def produce(self, request, pk=None):
        o = self.get_object()
        prod_id = request.data.get("production_order_id")
        if not prod_id:
            raise ValidationError("production_order_id обязателен")
        try:
            o = OrderService.produce(
                company_id=self.get_company_id(),
                order_id=o.id,
                production_order_id=int(prod_id),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(o).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        o = self.get_object()
        try:
            o = OrderService.cancel(
                company_id=self.get_company_id(), order_id=o.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OrderDetailSerializer(o).data)


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

    def perform_destroy(self, instance):
        OrderLineService.delete(
            company_id=self.get_company_id(), line_id=instance.id,
        )


# ============================================================
# Отгрузки
# ============================================================

class ShipmentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Shipment.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        return qs.order_by("-shipment_date")

    def perform_create(self, serializer):
        serializer.instance = ShipmentService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        s = self.get_object()
        try:
            s = ShipmentService.ship(
                company_id=self.get_company_id(), shipment_id=s.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ShipmentSerializer(s).data)

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        s = self.get_object()
        try:
            s = ShipmentService.deliver(
                company_id=self.get_company_id(), shipment_id=s.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ShipmentSerializer(s).data)


class ShipmentLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ShipmentLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShipmentLine.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = ShipmentLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Возвраты
# ============================================================

class ReturnViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Return.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        return qs.order_by("-return_date")

    def perform_create(self, serializer):
        serializer.instance = ReturnService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        r = self.get_object()
        try:
            r = ReturnService.approve(
                company_id=self.get_company_id(), return_id=r.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ReturnSerializer(r).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        r = self.get_object()
        try:
            r = ReturnService.receive(
                company_id=self.get_company_id(), return_id=r.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ReturnSerializer(r).data)


class ReturnLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ReturnLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReturnLine.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = ReturnLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Счета
# ============================================================

class InvoiceViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Invoice.objects.filter(company_id=self.get_company_id())
        o = self.request.query_params.get("order_id")
        if o:
            qs = qs.filter(order_id=o)
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs.order_by("-invoice_date")

    def perform_create(self, serializer):
        serializer.instance = InvoiceService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        inv = self.get_object()
        try:
            inv = InvoiceService.send(
                company_id=self.get_company_id(), invoice_id=inv.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InvoiceSerializer(inv).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        inv = self.get_object()
        amount = request.data.get("paid_amount")
        if amount is None:
            raise ValidationError("paid_amount обязателен")
        inv = InvoiceService.pay(
            company_id=self.get_company_id(),
            invoice_id=inv.id, paid_amount=amount,
        )
        return Response(InvoiceSerializer(inv).data)