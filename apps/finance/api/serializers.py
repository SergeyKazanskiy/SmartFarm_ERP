"""
DRF-сериализаторы Finance.
"""
from rest_framework import serializers

from apps.finance.models import (
    BankAccount, Budget, BudgetItem, CashAccount, CostCenter,
    ExchangeRate, FinAccount, FinancialIndicator, FinancialPeriod,
    FinancialProject, FinancialTransaction, Invoice, InvoiceLine, Payment,
)


class FinAccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(
        source="get_account_type_display", read_only=True,
    )

    class Meta:
        model = FinAccount
        fields = [
            "id", "code", "account_code", "account_name",
            "account_type", "account_type_display",
        ]


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = ["id", "code", "name"]


class FinancialProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProject
        fields = [
            "id", "code", "name",
            "linked_object_type", "linked_object_id",
        ]


class CashAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashAccount
        fields = ["id", "code", "name"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["id", "code", "bank_id", "account_number", "currency_id"]


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ["id", "code", "currency_id", "rate_date", "rate_value"]


# --- Бюджеты ---

class BudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = ["id", "code", "budget", "cost_center", "planned_amount"]


class BudgetSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = BudgetItemSerializer(many=True, read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id", "code", "financial_project", "period_from", "period_to",
            "status", "status_display",
            "approved_by_employee_id", "approved_at",
            "items",
        ]
        read_only_fields = ["approved_by_employee_id", "approved_at"]


# --- Счета ---

class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ["id", "code", "invoice", "description", "amount"]


class InvoiceListSerializer(serializers.ModelSerializer):
    invoice_type_display = serializers.CharField(
        source="get_invoice_type_display", read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "code", "invoice_type", "invoice_type_display",
            "counterparty_id", "invoice_number",
            "invoice_date", "due_date", "amount", "currency_id",
            "status", "status_display",
            "source_object_type", "source_object_id",
        ]


class InvoiceDetailSerializer(InvoiceListSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ["contract_id", "lines"]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "code", "invoice_type", "counterparty_id", "contract_id",
            "source_object_type", "source_object_id",
            "invoice_number", "invoice_date", "due_date",
            "amount", "currency_id",
        ]


# --- Платежи ---

class PaymentSerializer(serializers.ModelSerializer):
    payment_status_display = serializers.CharField(
        source="get_payment_status_display", read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id", "code", "invoice", "bank_account", "cash_account",
            "payment_status", "payment_status_display",
            "payment_date", "amount",
        ]
        read_only_fields = ["payment_status"]


# --- Проводки ---

class FinancialTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialTransaction
        fields = [
            "id", "code", "debit_account", "credit_account",
            "cost_center", "payment", "amount", "transaction_date",
        ]


# --- Периоды и показатели ---

class FinancialPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialPeriod
        fields = ["id", "code", "name", "date_from", "date_to", "is_closed"]
        read_only_fields = ["is_closed"]


class FinancialIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialIndicator
        fields = [
            "id", "code", "financial_project", "period",
            "indicator_code", "indicator_value",
        ]