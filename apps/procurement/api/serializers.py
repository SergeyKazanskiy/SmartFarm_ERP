"""
DRF-сериализаторы Procurement.
"""
from rest_framework import serializers

from apps.procurement.models import (
    Delivery, Order, OrderHistory, OrderLine, Requisition,
    RequisitionLine, RFQ, RFQSupplier, Supplier, SupplierQuote,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id", "code", "counterparty_id", "rating",
            "payment_terms", "delivery_terms", "lead_time_days",
            "is_preferred", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class RequisitionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisitionLine
        fields = [
            "id", "code", "requisition", "material_id",
            "quantity", "unit_id", "estimated_unit_cost",
        ]


class RequisitionListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Requisition
        fields = [
            "id", "code", "requisition_number", "source_type", "source_id",
            "requisition_date", "required_date", "status", "status_display",
            "requested_by_employee_id",
        ]


class RequisitionDetailSerializer(RequisitionListSerializer):
    lines = RequisitionLineSerializer(many=True, read_only=True)

    class Meta(RequisitionListSerializer.Meta):
        fields = RequisitionListSerializer.Meta.fields + [
            "planned_order_date", "lines",
        ]


class RequisitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisition
        fields = [
            "code", "requisition_number", "source_type", "source_id",
            "requisition_date", "planned_order_date", "required_date",
            "requested_by_employee_id",
        ]


class RFQSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQSupplier
        fields = ["id", "code", "rfq", "supplier"]


class SupplierQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierQuote
        fields = [
            "id", "code", "rfq_supplier", "material_id",
            "unit_price", "quantity", "delivery_days",
        ]


class RFQListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RFQ
        fields = [
            "id", "code", "rfq_number", "requisition",
            "rfq_date", "response_deadline", "status", "status_display",
        ]


class RFQDetailSerializer(RFQListSerializer):
    suppliers = RFQSupplierSerializer(many=True, read_only=True)

    class Meta(RFQListSerializer.Meta):
        fields = RFQListSerializer.Meta.fields + ["suppliers"]


class RFQCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQ
        fields = ["code", "rfq_number", "requisition", "rfq_date", "response_deadline"]


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            "id", "code", "order", "material_id",
            "quantity", "unit_price", "total_price", "received_quantity",
        ]
        read_only_fields = ["total_price", "received_quantity"]


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "code", "order_number", "supplier",
            "requisition", "rfq",
            "order_date", "expected_delivery_date", "actual_delivery_date",
            "status", "status_display", "total_amount", "currency_id",
        ]


class OrderDetailSerializer(OrderListSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    history = serializers.SerializerMethodField()

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + ["lines", "history"]

    def get_history(self, obj):
        return OrderHistorySerializer(obj.history.all(), many=True).data


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "code", "order_number", "supplier", "requisition", "rfq",
            "order_date", "expected_delivery_date", "currency_id",
        ]


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderHistory
        fields = [
            "id", "order", "changed_at", "changed_by_employee_id",
            "status_from", "status_to", "comment",
        ]
        read_only_fields = fields


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = [
            "id", "code", "order", "delivery_date",
            "quantity", "status",
        ]