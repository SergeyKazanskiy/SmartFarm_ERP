"""
DRF-сериализаторы Production.
"""
from rest_framework import serializers

from apps.production.models import (
    Bom, BomItem, MaterialPriceHistory, OperationDefinition,
    OperationExecution, ProductionOrder, QualityPoint,
    Routing, Technology, WorkCenter, WorkOrder,
)


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ["id", "code", "name"]


class WorkCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCenter
        fields = ["id", "code", "name"]


class RoutingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Routing
        fields = ["id", "code", "technology", "name"]


class OperationDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationDefinition
        fields = [
            "id", "code", "routing", "name", "sequence_no",
            "work_center", "resources_json", "parameters_json",
        ]


class QualityPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityPoint
        fields = ["id", "code", "operation", "name"]


class BomItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BomItem
        fields = ["id", "code", "bom", "material_id", "quantity", "unit_cost"]


class BomSerializer(serializers.ModelSerializer):
    items = BomItemSerializer(many=True, read_only=True)

    class Meta:
        model = Bom
        fields = ["id", "code", "product_material_id", "name", "items"]


class MaterialPriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialPriceHistory
        fields = [
            "id", "code", "material_id", "unit_cost",
            "effective_date", "created_by_employee_id",
        ]
        read_only_fields = ["created_by_employee_id"]


class ProductionOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ProductionOrder
        fields = [
            "id", "code", "bom", "routing", "planned_quantity",
            "planned_start_date", "planned_end_date",
            "status", "status_display",
        ]
        read_only_fields = ["status"]


class WorkOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            "id", "code", "production_order",
            "status", "status_display",
            "planned_start", "planned_finish",
            "actual_start", "actual_finish",
            "actual_materials_json",
        ]
        read_only_fields = [
            "status", "actual_start", "actual_finish",
        ]


class OperationExecutionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OperationExecution
        fields = [
            "id", "code", "work_order", "operation", "work_center",
            "performed_by_employee_id",
            "start_time", "end_time", "status", "status_display",
            "measurements_json", "quality_results_json",
        ]
        read_only_fields = [
            "status", "start_time", "end_time",
        ]