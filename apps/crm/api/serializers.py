"""
DRF-сериализаторы CRM.
"""
from rest_framework import serializers

from apps.crm.models import (
    Activity, ActivityType, CommercialOffer, CommercialOfferLine,
    Contact, Contract, Lead, LeadSource, LeadStatus,
    Opportunity, OpportunityStage, PriceList, PriceListItem,
    SalesFunnel,
)


# --- Справочники ---

class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = ["id", "code", "name"]


class LeadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatus
        fields = ["id", "code", "name"]


class OpportunityStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityStage
        fields = ["id", "code", "name"]


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ["id", "code", "name"]


class SalesFunnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesFunnel
        fields = ["id", "code", "name", "stages_json"]


# --- Лиды ---

class LeadListSerializer(serializers.ModelSerializer):
    lead_status_name = serializers.CharField(source="lead_status.name", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "code", "title", "lead_status", "lead_status_name",
            "lead_source", "counterparty_id", "responsible_employee_id",
            "contact_name", "contact_phone", "created_at",
        ]


class LeadDetailSerializer(LeadListSerializer):
    activities = serializers.SerializerMethodField()

    class Meta(LeadListSerializer.Meta):
        fields = LeadListSerializer.Meta.fields + [
            "description", "contact_email", "updated_at", "activities",
        ]

    def get_activities(self, obj):
        return ActivitySerializer(obj.activities.all(), many=True).data


class LeadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "code", "title", "description", "lead_source", "lead_status",
            "counterparty_id", "responsible_employee_id",
            "contact_name", "contact_phone", "contact_email",
        ]


# --- Контакты ---

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            "id", "code", "natural_person_id", "counterparty_id",
            "position", "phone", "email", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# --- Сделки ---

class OpportunityListSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(
        source="opportunity_stage.name", read_only=True,
    )
    is_won_display = serializers.CharField(source="get_is_won_display", read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id", "code", "title", "lead", "opportunity_stage", "stage_name",
            "amount", "expected_close_date", "is_won", "is_won_display",
            "responsible_employee_id", "created_at",
        ]


class OpportunityDetailSerializer(OpportunityListSerializer):
    class Meta(OpportunityListSerializer.Meta):
        fields = OpportunityListSerializer.Meta.fields + [
            "lost_reason", "updated_at",
        ]


class OpportunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = [
            "code", "title", "lead", "opportunity_stage",
            "responsible_employee_id", "amount", "expected_close_date",
        ]


# --- Активности ---

class ActivitySerializer(serializers.ModelSerializer):
    activity_type_name = serializers.CharField(
        source="activity_type.name", read_only=True,
    )

    class Meta:
        model = Activity
        fields = [
            "id", "code", "activity_type", "activity_type_name",
            "lead", "opportunity", "employee_id",
            "activity_date", "is_completed", "subject", "result",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# --- КП ---

class CommercialOfferLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommercialOfferLine
        fields = [
            "id", "offer", "price_list_item", "description",
            "quantity", "unit_price", "line_amount",
        ]
        read_only_fields = ["line_amount"]


class CommercialOfferListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CommercialOffer
        fields = [
            "id", "code", "opportunity", "offer_date",
            "status", "status_display", "total_amount",
        ]


class CommercialOfferDetailSerializer(CommercialOfferListSerializer):
    lines = CommercialOfferLineSerializer(many=True, read_only=True)

    class Meta(CommercialOfferListSerializer.Meta):
        fields = CommercialOfferListSerializer.Meta.fields + ["lines"]


# --- Прайс-листы ---

class PriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceList
        fields = ["id", "code", "name", "valid_from"]


class PriceListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceListItem
        fields = [
            "id", "code", "price_list", "item_type",
            "material_id", "service_name", "unit_id", "price",
        ]


# --- Договоры ---

class ContractListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "code", "counterparty_id", "contract_number",
            "contract_date", "contract_amount", "status", "status_display",
        ]


class ContractDetailSerializer(ContractListSerializer):
    class Meta(ContractListSerializer.Meta):
        fields = ContractListSerializer.Meta.fields + ["covered_objects_json"]


class ContractCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = [
            "code", "counterparty_id", "contract_number",
            "contract_date", "contract_amount", "covered_objects_json",
        ]