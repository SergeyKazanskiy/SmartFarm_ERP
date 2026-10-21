"""
DRF-сериализаторы CP.
"""
from rest_framework import serializers

from apps.cp.models import (
    Address, Attachment, BankAccount, Blacklist, Category, ContactPerson,
    Contract, Counterparty, CounterpartyType, Interaction, Rating,
)


class CounterpartyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CounterpartyType
        fields = ["id", "code", "name", "is_active"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "code", "name", "parent", "is_active"]


class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPerson
        fields = [
            "id", "code", "first_name", "last_name", "middle_name",
            "position", "department", "phone", "mobile_phone", "email",
            "is_primary", "is_active",
        ]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id", "code", "bank_name", "bank_code",
            "account_number", "currency_id", "is_primary", "is_active",
        ]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "code", "address_type", "address_line1", "address_line2",
            "city", "region", "postal_code", "country_id",
            "is_primary", "is_active",
        ]


class CounterpartyListSerializer(serializers.ModelSerializer):
    counterparty_type_name = serializers.CharField(
        source="counterparty_type.name", read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Counterparty
        fields = [
            "id", "code", "internal_code", "name",
            "counterparty_type", "counterparty_type_name",
            "status", "status_display", "is_blacklisted",
            "phone", "email", "responsible_employee_id",
        ]


class CounterpartyDetailSerializer(CounterpartyListSerializer):
    contacts = ContactPersonSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta(CounterpartyListSerializer.Meta):
        fields = CounterpartyListSerializer.Meta.fields + [
            "short_name", "tax_id", "tax_registration_id", "vat_registration",
            "legal_address", "actual_address", "website", "industry",
            "credit_limit", "payment_terms", "delivery_terms",
            "created_at", "updated_at",
            "contacts", "bank_accounts", "addresses",
        ]
        read_only_fields = fields


class CounterpartyCreateSerializer(serializers.ModelSerializer):
    """Только поля, которые можно передать при создании/обновлении."""

    class Meta:
        model = Counterparty
        fields = [
            "code", "internal_code",
            "counterparty_type", "category",
            "name", "short_name",
            "tax_id", "tax_registration_id", "vat_registration",
            "legal_address", "actual_address",
            "phone", "email", "website", "industry",
            "credit_limit", "payment_terms", "delivery_terms",
            "responsible_employee_id",
        ]


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = [
            "id", "counterparty", "rating_date", "rating_value",
            "rating_type", "comment", "rated_by_employee_id",
        ]
        read_only_fields = ["rated_by_employee_id"]


class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = [
            "id", "counterparty", "interaction_type", "interaction_date",
            "contact_person", "employee_id", "subject", "description",
            "result", "next_action_date",
        ]
        read_only_fields = ["employee_id", "interaction_date"]


class ContractSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "code", "counterparty", "contract_number", "contract_date",
            "valid_from", "valid_to", "contract_type", "amount",
            "currency_id", "status", "status_display",
        ]
        read_only_fields = ["status"]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            "id", "code", "counterparty", "document_id",
            "attachment_type", "description",
        ]


class BlacklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blacklist
        fields = [
            "id", "counterparty", "block_date", "reason",
            "blocked_by_employee_id", "unblock_date",
            "unblock_reason", "unblocked_by_employee_id",
        ]
        read_only_fields = fields