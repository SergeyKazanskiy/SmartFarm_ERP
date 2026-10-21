"""
DRF ViewSets CP. Все запросы фильтруются по текущей компании пользователя.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cp.api.serializers import (
    AddressSerializer, AttachmentSerializer, BankAccountSerializer,
    BlacklistSerializer, CategorySerializer, ContactPersonSerializer,
    ContractSerializer, CounterpartyCreateSerializer,
    CounterpartyDetailSerializer, CounterpartyListSerializer,
    CounterpartyTypeSerializer, InteractionSerializer, RatingSerializer,
)
from apps.cp.models import (
    Address, Attachment, BankAccount, Blacklist, Category, ContactPerson,
    Contract, Counterparty, CounterpartyType, Interaction, Rating,
)
from apps.cp.services import (
    AddressService, AttachmentService, BankAccountService,
    BlacklistService, CategoryService, ContactPersonService,
    ContractService, CounterpartyService, CounterpartyTypeService,
    InteractionService, RatingService,
)


class CompanyScopedMixin:
    """Фильтр по активной компании пользователя."""

    def get_company_id(self) -> int:
        company_id = getattr(self.request.user, "current_company_id", None)
        if not company_id:
            raise PermissionDenied("Компания не выбрана")
        return company_id

    def get_employee_id(self) -> int | None:
        return getattr(self.request.user, "hr_employee_id", None)


# ------------------------------------------------------------
# Справочники
# ------------------------------------------------------------

class CounterpartyTypeViewSet(viewsets.ModelViewSet):
    serializer_class = CounterpartyTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CounterpartyType.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("name")

    def perform_create(self, serializer):
        data = serializer.validated_data
        instance = CounterpartyTypeService.save(
            company_id=self.request.user.current_company_id,
            data={
                "code": data.get("code"),
                "name": data["name"],
                "is_active": data.get("is_active", True),
            },
        )
        serializer.instance = instance


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("name")


# ------------------------------------------------------------
# Контрагент
# ------------------------------------------------------------

class CounterpartyViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Counterparty.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("counterparty_type").prefetch_related(
            "contacts", "bank_accounts", "addresses",
        )
        if self.action == "list":
            status_filter = self.request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)
            if self.request.query_params.get("blacklisted") == "true":
                qs = qs.filter(is_blacklisted=True)
            search = self.request.query_params.get("search")
            if search:
                from django.db.models import Q
                qs = qs.filter(
                    Q(name__icontains=search)
                    | Q(code__icontains=search)
                    | Q(tax_id__icontains=search)
                )
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CounterpartyDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return CounterpartyCreateSerializer
        return CounterpartyListSerializer

    def perform_create(self, serializer):
        instance = CounterpartyService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = CounterpartyService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
            actor_employee_id=self.get_employee_id(),
        )
        serializer.instance = instance

    # ---------- Экшены ----------

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        cp = self.get_object()
        new_status = request.data.get("status")
        try:
            cp = CounterpartyService.update_status(
                company_id=self.get_company_id(),
                counterparty_id=cp.id,
                new_status=new_status,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(CounterpartyDetailSerializer(cp).data)

    @action(detail=True, methods=["post"], url_path="assign-responsible")
    def assign_responsible(self, request, pk=None):
        cp = self.get_object()
        employee_id = request.data.get("employee_id")
        if not employee_id:
            raise ValidationError("employee_id обязателен")
        cp = CounterpartyService.assign_responsible(
            company_id=self.get_company_id(),
            counterparty_id=cp.id,
            employee_id=int(employee_id),
        )
        return Response(CounterpartyDetailSerializer(cp).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        cp = self.get_object()
        reason = request.data.get("reason", "")
        BlacklistService.add(
            company_id=self.get_company_id(),
            counterparty_id=cp.id,
            reason=reason,
            actor_employee_id=self.get_employee_id(),
        )
        cp.refresh_from_db()
        return Response(CounterpartyDetailSerializer(cp).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        cp = self.get_object()
        reason = request.data.get("reason", "")
        try:
            BlacklistService.remove(
                company_id=self.get_company_id(),
                counterparty_id=cp.id,
                unblock_reason=reason,
                actor_employee_id=self.get_employee_id(),
            )
        except ValueError as e:
            raise ValidationError(str(e))
        cp.refresh_from_db()
        return Response(CounterpartyDetailSerializer(cp).data)


# ------------------------------------------------------------
# Дочерние сущности: контакты / счета / адреса
# ------------------------------------------------------------

class ContactPersonViewSet(viewsets.ModelViewSet):
    serializer_class = ContactPersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContactPerson.objects.filter(
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        instance = ContactPersonService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = ContactPersonService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )
        serializer.instance = instance

    def perform_destroy(self, instance):
        ContactPersonService.delete(
            company_id=self.request.user.current_company_id,
            contact_id=instance.id,
        )


class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        instance = BankAccountService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
        )
        serializer.instance = instance


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        instance = AddressService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
        )
        serializer.instance = instance


# ------------------------------------------------------------
# Рейтинги, взаимодействия
# ------------------------------------------------------------

class RatingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Rating.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("-rating_date")

    def perform_create(self, serializer):
        instance = RatingService.create(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            actor_employee_id=getattr(self.request.user, "hr_employee_id", None),
        )
        serializer.instance = instance


class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Interaction.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("-interaction_date")

    def perform_create(self, serializer):
        instance = InteractionService.create(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            actor_employee_id=getattr(self.request.user, "hr_employee_id", None),
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = InteractionService.update(
            company_id=self.request.user.current_company_id,
            interaction_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )
        serializer.instance = instance


# ------------------------------------------------------------
# Договоры, вложения
# ------------------------------------------------------------

class ContractViewSet(viewsets.ModelViewSet):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contract.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("-contract_date")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        instance = ContractService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            actor_employee_id=getattr(self.request.user, "hr_employee_id", None),
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = ContractService.save(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            instance=serializer.instance,
            actor_employee_id=getattr(self.request.user, "hr_employee_id", None),
        )
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        contract = self.get_object()
        try:
            contract = ContractService.activate(
                company_id=self.request.user.current_company_id,
                contract_id=contract.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ContractSerializer(contract).data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        contract = self.get_object()
        try:
            contract = ContractService.terminate(
                company_id=self.request.user.current_company_id,
                contract_id=contract.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ContractSerializer(contract).data)


class AttachmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Attachment.objects.filter(
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        instance = AttachmentService.create(
            company_id=self.request.user.current_company_id,
            data=dict(serializer.validated_data),
            actor_employee_id=getattr(self.request.user, "hr_employee_id", None),
        )
        serializer.instance = instance

    def perform_destroy(self, instance):
        AttachmentService.delete(
            company_id=self.request.user.current_company_id,
            attachment_id=instance.id,
        )


# ------------------------------------------------------------
# Чёрный список (только чтение)
# ------------------------------------------------------------

class BlacklistViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BlacklistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Blacklist.objects.filter(
            company_id=self.request.user.current_company_id,
        ).order_by("-block_date")