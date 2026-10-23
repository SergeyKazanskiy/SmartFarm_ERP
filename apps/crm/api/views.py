"""
DRF ViewSets CRM. Все запросы фильтруются по активной компании пользователя.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.crm.api.serializers import (
    ActivitySerializer, ActivityTypeSerializer,
    CommercialOfferDetailSerializer, CommercialOfferLineSerializer,
    CommercialOfferListSerializer, ContactSerializer,
    ContractCreateSerializer, ContractDetailSerializer, ContractListSerializer,
    LeadCreateSerializer, LeadDetailSerializer, LeadListSerializer,
    LeadSourceSerializer, LeadStatusSerializer,
    OpportunityCreateSerializer, OpportunityDetailSerializer, OpportunityListSerializer,
    OpportunityStageSerializer, PriceListItemSerializer, PriceListSerializer,
    SalesFunnelSerializer,
)
from apps.crm.models import (
    Activity, ActivityType, CommercialOffer, CommercialOfferLine,
    Contact, Contract, Lead, LeadSource, LeadStatus,
    Opportunity, OpportunityStage, PriceList, PriceListItem, SalesFunnel,
)
from apps.crm.services import (
    ActivityService, CommercialOfferLineService, CommercialOfferService,
    ContactService, ContractService, LeadService,
    OpportunityService, PriceListItemService, PriceListService,
)


class CompanyScopedMixin:
    def get_company_id(self) -> int:
        company_id = getattr(self.request.user, "current_company_id", None)
        if not company_id:
            raise PermissionDenied("Компания не выбрана")
        return company_id

    def get_employee_id(self) -> int | None:
        return getattr(self.request.user, "hr_employee_id", None)


# --- Справочники: один универсальный ViewSet на 5 моделей ---

class _BaseReferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    MODEL = None

    def get_queryset(self):
        return self.MODEL.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("name")


class LeadSourceViewSet(_BaseReferenceViewSet):
    serializer_class = LeadSourceSerializer
    MODEL = LeadSource


class LeadStatusViewSet(_BaseReferenceViewSet):
    serializer_class = LeadStatusSerializer
    MODEL = LeadStatus


class OpportunityStageViewSet(_BaseReferenceViewSet):
    serializer_class = OpportunityStageSerializer
    MODEL = OpportunityStage


class ActivityTypeViewSet(_BaseReferenceViewSet):
    serializer_class = ActivityTypeSerializer
    MODEL = ActivityType


class SalesFunnelViewSet(_BaseReferenceViewSet):
    serializer_class = SalesFunnelSerializer
    MODEL = SalesFunnel


# --- Лиды ---

class LeadViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Lead.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("lead_status", "lead_source")
        if self.action == "list":
            s = self.request.query_params.get("status")
            if s:
                qs = qs.filter(lead_status_id=s)
            r = self.request.query_params.get("responsible")
            if r:
                qs = qs.filter(responsible_employee_id=r)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return LeadDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return LeadCreateSerializer
        return LeadListSerializer

    def perform_create(self, serializer):
        serializer.instance = LeadService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        lead = self.get_object()
        employee_id = request.data.get("employee_id")
        if not employee_id:
            raise ValidationError("employee_id обязателен")
        lead = LeadService.assign(
            company_id=self.get_company_id(),
            lead_id=lead.id,
            employee_id=int(employee_id),
        )
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        lead = self.get_object()
        status_id = request.data.get("lead_status_id")
        if not status_id:
            raise ValidationError("lead_status_id обязателен")
        lead = LeadService.update_status(
            company_id=self.get_company_id(),
            lead_id=lead.id,
            new_status_id=int(status_id),
        )
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=["post"], url_path="link-counterparty")
    def link_counterparty(self, request, pk=None):
        lead = self.get_object()
        counterparty_id = request.data.get("counterparty_id")
        if not counterparty_id:
            raise ValidationError("counterparty_id обязателен")
        lead = LeadService.link_counterparty(
            company_id=self.get_company_id(),
            lead_id=lead.id,
            counterparty_id=int(counterparty_id),
        )
        return Response(LeadDetailSerializer(lead).data)


# --- Контакты ---

class ContactViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(
            company_id=self.get_company_id(),
        )

    def perform_create(self, serializer):
        serializer.instance = ContactService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = ContactService.update(
            company_id=self.get_company_id(),
            contact_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )


# --- Сделки ---

class OpportunityViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Opportunity.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("opportunity_stage", "lead")
        if self.action == "list":
            st = self.request.query_params.get("stage")
            if st:
                qs = qs.filter(opportunity_stage_id=st)
            won = self.request.query_params.get("is_won")
            if won in ("0", "1"):
                qs = qs.filter(is_won=int(won))
            elif won == "null":
                qs = qs.filter(is_won__isnull=True)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OpportunityDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return OpportunityCreateSerializer
        return OpportunityListSerializer

    def perform_create(self, serializer):
        serializer.instance = OpportunityService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"], url_path="update-stage")
    def update_stage(self, request, pk=None):
        opp = self.get_object()
        stage_id = request.data.get("opportunity_stage_id")
        if not stage_id:
            raise ValidationError("opportunity_stage_id обязателен")
        try:
            opp = OpportunityService.update_stage(
                company_id=self.get_company_id(),
                opportunity_id=opp.id,
                stage_id=int(stage_id),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OpportunityDetailSerializer(opp).data)

    @action(detail=True, methods=["post"])
    def win(self, request, pk=None):
        opp = self.get_object()
        try:
            opp = OpportunityService.win(
                company_id=self.get_company_id(),
                opportunity_id=opp.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OpportunityDetailSerializer(opp).data)

    @action(detail=True, methods=["post"])
    def lose(self, request, pk=None):
        opp = self.get_object()
        reason = request.data.get("lost_reason", "")
        try:
            opp = OpportunityService.lose(
                company_id=self.get_company_id(),
                opportunity_id=opp.id,
                lost_reason=reason,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(OpportunityDetailSerializer(opp).data)


# --- Активности ---

class ActivityViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("activity_type")

    def perform_create(self, serializer):
        serializer.instance = ActivityService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        act = self.get_object()
        result = request.data.get("result", "")
        if not result:
            raise ValidationError("result обязателен")
        try:
            act = ActivityService.complete(
                company_id=self.get_company_id(),
                activity_id=act.id,
                result=result,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ActivitySerializer(act).data)


# --- КП ---

class CommercialOfferViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommercialOffer.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CommercialOfferDetailSerializer
        return CommercialOfferListSerializer

    def perform_create(self, serializer):
        serializer.instance = CommercialOfferService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        offer = self.get_object()
        try:
            offer = CommercialOfferService.send(
                company_id=self.get_company_id(), offer_id=offer.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(CommercialOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        try:
            offer = CommercialOfferService.accept(
                company_id=self.get_company_id(), offer_id=offer.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(CommercialOfferDetailSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        offer = self.get_object()
        try:
            offer = CommercialOfferService.decline(
                company_id=self.get_company_id(), offer_id=offer.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(CommercialOfferDetailSerializer(offer).data)


class CommercialOfferLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = CommercialOfferLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommercialOfferLine.objects.filter(
            company_id=self.get_company_id(),
        )

    def perform_create(self, serializer):
        serializer.instance = CommercialOfferLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# --- Прайс-листы ---

class PriceListViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceList.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = PriceListService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class PriceListItemViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PriceListItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceListItem.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = PriceListItemService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"], url_path="update-price")
    def update_price(self, request, pk=None):
        item = self.get_object()
        price = request.data.get("price")
        if price is None:
            raise ValidationError("price обязателен")
        item = PriceListItemService.update_price(
            company_id=self.get_company_id(),
            price_list_item_id=item.id,
            price=price,
        )
        return Response(PriceListItemSerializer(item).data)


# --- Договоры ---

class ContractViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contract.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            s = self.request.query_params.get("status")
            if s:
                qs = qs.filter(status=s)
            cp = self.request.query_params.get("counterparty_id")
            if cp:
                qs = qs.filter(counterparty_id=cp)
        return qs.order_by("-contract_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ContractDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContractCreateSerializer
        return ContractListSerializer

    def perform_create(self, serializer):
        serializer.instance = ContractService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        c = self.get_object()
        try:
            c = ContractService.activate(
                company_id=self.get_company_id(), contract_id=c.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ContractDetailSerializer(c).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        c = self.get_object()
        try:
            c = ContractService.complete(
                company_id=self.get_company_id(), contract_id=c.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ContractDetailSerializer(c).data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        c = self.get_object()
        try:
            c = ContractService.terminate(
                company_id=self.get_company_id(), contract_id=c.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ContractDetailSerializer(c).data)

    @action(detail=True, methods=["post"], url_path="update-covered-objects")
    def update_covered_objects(self, request, pk=None):
        c = self.get_object()
        objects = request.data.get("covered_objects_json", [])
        c = ContractService.update_covered_objects(
            company_id=self.get_company_id(),
            contract_id=c.id,
            covered_objects_json=objects,
        )
        return Response(ContractDetailSerializer(c).data)