"""
DRF-сериализаторы Sales.
"""
from rest_framework import serializers

from apps.sales.models import (
    Customer, Invoice, Opportunity, Order, OrderLine,
    PriceList, PriceListLine, Quote, QuoteLine,
    Return, ReturnLine, Shipment, ShipmentLine,
)


class CustomerSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "code", "counterparty_id", "category", "category_display",
            "credit_limit", "payment_terms", "default_price_list",
            "sales_manager_employee_id", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PriceListLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceListLine
        fields = ["id", "code", "price_list", "material_id", "unit_price", "min_quantity"]


class PriceListSerializer(serializers.ModelSerializer):
    lines = PriceListLineSerializer(many=True, read_only=True)

    class Meta:
        model = PriceList
        fields = [
            "id", "code", "name", "currency_id", "valid_from", "valid_to",
            "is_default", "lines",
        ]


class OpportunitySerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id", "code", "customer", "name", "stage", "stage_display",
            "expected_value", "probability_percent", "expected_close_date",
            "created_by_employee_id", "created_at", "updated_at",
        ]
        read_only_fields = ["probability_percent", "created_at", "updated_at"]


class QuoteLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteLine
        fields = [
            "id", "code", "quote", "material_id", "price_list_item",
            "quantity", "unit_price", "discount_percent", "total_price",
        ]
        read_only_fields = ["total_price"]


class QuoteListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id", "code", "quote_number", "customer", "opportunity",
            "quote_date", "valid_until", "total_amount",
            "status", "status_display", "created_at",
        ]
        read_only_fields = ["total_amount", "created_at"]


class QuoteDetailSerializer(QuoteListSerializer):
    lines = QuoteLineSerializer(many=True, read_only=True)

    class Meta(QuoteListSerializer.Meta):
        fields = QuoteListSerializer.Meta.fields + ["lines"]


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            "id", "code", "order", "material_id",
            "quantity", "unit_price", "discount_percent",
            "total_price", "shipped_quantity",
        ]
        read_only_fields = ["total_price", "shipped_quantity"]


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "code", "order_number", "customer", "quote",
            "order_date", "order_type", "status", "status_display",
            "total_amount", "currency_id", "expected_ship_date",
            "created_at",
        ]
        read_only_fields = ["total_amount", "created_at"]


class OrderDetailSerializer(OrderListSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "actual_ship_date", "delivery_address_id",
            "created_by_employee_id", "production_order_id", "lines",
        ]


class ShipmentLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentLine
        fields = ["id", "code", "shipment", "order_line", "quantity"]


class ShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = ShipmentLineSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id", "code", "shipment_number", "order", "warehouse_id",
            "shipment_date", "status", "status_display",
            "tracking_number", "shipping_method_id", "lines",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ReturnLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnLine
        fields = ["id", "code", "return_", "order_line", "quantity"]


class ReturnSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = ReturnLineSerializer(many=True, read_only=True)

    class Meta:
        model = Return
        fields = [
            "id", "code", "return_number", "order", "return_date",
            "reason", "status", "status_display", "lines",
        ]
        read_only_fields = ["created_at", "updated_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "code", "invoice_number", "order", "invoice_date",
            "due_date", "total_amount", "status", "status_display",
            "paid_amount", "created_at", "updated_at",
        ]
        read_only_fields = ["paid_amount", "created_at", "updated_at"]