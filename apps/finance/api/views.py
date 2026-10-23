"""
DRF ViewSets Finance. Все запросы фильтруются по активной компании пользователя.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.finance.api.serializers import (
    BankAccountSerializer, BudgetItemSerializer, BudgetSerializer,
    CashAccountSerializer, CostCenterSerializer, ExchangeRateSerializer,
    FinAccountSerializer, FinancialIndicatorSerializer,
    FinancialPeriodSerializer, FinancialProjectSerializer,
    FinancialTransactionSerializer, InvoiceCreateSerializer,
    InvoiceDetailSerializer, InvoiceLineSerializer, InvoiceListSerializer,
    PaymentSerializer,
)
from apps.finance.models import (
    BankAccount, Budget, BudgetItem, CashAccount, CostCenter,
    ExchangeRate, FinAccount, FinancialIndicator, FinancialPeriod,
    FinancialProject, FinancialTransaction, Invoice, InvoiceLine, Payment,
)
from apps.finance.services import (
    AccountService, BankAccountService, BudgetItemService, BudgetService,
    CashAccountService, CostCenterService, ExchangeRateService,
    FinancialIndicatorService, FinancialPeriodService,
    FinancialProjectService, FinancialTransactionService,
    InvoiceLineService, InvoiceService, PaymentService,
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
# Справочники
# ============================================================

class FinAccountViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FinAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinAccount.objects.filter(
            company_id=self.get_company_id(),
        ).order_by("account_code")

    def perform_create(self, serializer):
        serializer.instance = AccountService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class CostCenterViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CostCenterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CostCenter.objects.filter(
            company_id=self.get_company_id(),
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.instance = CostCenterService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class FinancialProjectViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = FinancialProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialProject.objects.filter(
            company_id=self.get_company_id(),
        ).order_by("name")

    def perform_create(self, serializer):
        serializer.instance = FinancialProjectService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class CashAccountViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CashAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CashAccount.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = CashAccountService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class BankAccountViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = BankAccountService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class ExchangeRateViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ExchangeRate.objects.filter(company_id=self.get_company_id())
        cid = self.request.query_params.get("currency_id")
        if cid:
            qs = qs.filter(currency_id=cid)
        return qs.order_by("-rate_date")

    def perform_create(self, serializer):
        serializer.instance = ExchangeRateService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Бюджеты
# ============================================================

class BudgetViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Budget.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("items")
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs.order_by("-period_from")

    def perform_create(self, serializer):
        serializer.instance = BudgetService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        b = self.get_object()
        eid = self.get_employee_id()
        if not eid:
            raise ValidationError("Пользователь не привязан к сотруднику")
        try:
            b = BudgetService.approve(
                company_id=self.get_company_id(),
                budget_id=b.id, approver_employee_id=eid,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(BudgetSerializer(b).data)


class BudgetItemViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = BudgetItem.objects.filter(company_id=self.get_company_id())
        b = self.request.query_params.get("budget_id")
        if b:
            qs = qs.filter(budget_id=b)
        return qs

    def perform_create(self, serializer):
        serializer.instance = BudgetItemService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = BudgetItemService.update_planned(
            company_id=self.get_company_id(),
            budget_item_id=serializer.instance.id,
            planned_amount=serializer.validated_data.get(
                "planned_amount", serializer.instance.planned_amount,
            ),
        )


# ============================================================
# Счета
# ============================================================

class InvoiceViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Invoice.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines", "payments")
        if self.action == "list":
            tp = self.request.query_params.get("invoice_type")
            if tp:
                qs = qs.filter(invoice_type=tp)
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
            cp = self.request.query_params.get("counterparty_id")
            if cp:
                qs = qs.filter(counterparty_id=cp)
        return qs.order_by("-invoice_date")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return InvoiceDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return InvoiceCreateSerializer
        return InvoiceListSerializer

    def perform_create(self, serializer):
        serializer.instance = InvoiceService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        inv = self.get_object()
        try:
            inv = InvoiceService.issue(
                company_id=self.get_company_id(), invoice_id=inv.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InvoiceDetailSerializer(inv).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        inv = self.get_object()
        try:
            inv = InvoiceService.cancel(
                company_id=self.get_company_id(), invoice_id=inv.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InvoiceDetailSerializer(inv).data)


class InvoiceLineViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InvoiceLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = InvoiceLine.objects.filter(company_id=self.get_company_id())
        i = self.request.query_params.get("invoice_id")
        if i:
            qs = qs.filter(invoice_id=i)
        return qs

    def perform_create(self, serializer):
        serializer.instance = InvoiceLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Платежи
# ============================================================

class PaymentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Payment.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            st = self.request.query_params.get("payment_status")
            if st:
                qs = qs.filter(payment_status=st)
            inv = self.request.query_params.get("invoice_id")
            if inv:
                qs = qs.filter(invoice_id=inv)
        return qs.order_by("-payment_date")

    def perform_create(self, serializer):
        serializer.instance = PaymentService.plan(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        p = self.get_object()
        try:
            p = PaymentService.complete(
                company_id=self.get_company_id(), payment_id=p.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(PaymentSerializer(p).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        p = self.get_object()
        try:
            p = PaymentService.cancel(
                company_id=self.get_company_id(), payment_id=p.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(PaymentSerializer(p).data)


# ============================================================
# Проводки
# ============================================================

class FinancialTransactionViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FinancialTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialTransaction.objects.filter(
            company_id=self.get_company_id(),
        ).order_by("-transaction_date")

    def perform_create(self, serializer):
        serializer.instance = FinancialTransactionService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# ============================================================
# Периоды и показатели
# ============================================================

class FinancialPeriodViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = FinancialPeriodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialPeriod.objects.filter(
            company_id=self.get_company_id(),
        ).order_by("-date_from")

    def perform_create(self, serializer):
        serializer.instance = FinancialPeriodService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        period = self.get_object()
        period = FinancialPeriodService.close(
            company_id=self.get_company_id(), period_id=period.id,
        )
        return Response(FinancialPeriodSerializer(period).data)


class FinancialIndicatorViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FinancialIndicatorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = FinancialIndicator.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("period_id")
        if p:
            qs = qs.filter(period_id=p)
        fp = self.request.query_params.get("financial_project_id")
        if fp:
            qs = qs.filter(financial_project_id=fp)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.instance = FinancialIndicatorService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )