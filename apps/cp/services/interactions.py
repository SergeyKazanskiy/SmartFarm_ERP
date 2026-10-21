"""
Рейтинги и взаимодействия.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import CPEvents as CP

from apps.cp.models import Interaction, Rating


class RatingService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CP-18."""
        rating = Rating.objects.create(
            company_id=company_id,
            counterparty_id=data["counterparty_id"],
            rating_date=data.get("rating_date") or timezone.now().date(),
            rating_value=data["rating_value"],
            rating_type=data.get("rating_type", "overall"),
            comment=data.get("comment", ""),
            rated_by_employee_id=actor_employee_id,
        )
        EventBus.publish(
            CP.RATING_CREATE,
            company_id=company_id,
            payload={
                "rating_id": rating.id,
                "counterparty_id": rating.counterparty_id,
                "rating_value": rating.rating_value,
                "rating_type": rating.rating_type,
            },
        )
        return rating


class InteractionService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CP-19."""
        interaction = Interaction.objects.create(
            company_id=company_id,
            counterparty_id=data["counterparty_id"],
            interaction_type=data["interaction_type"],
            interaction_date=data.get("interaction_date") or timezone.now(),
            contact_person_id=data.get("contact_person_id"),
            employee_id=actor_employee_id or data.get("employee_id"),
            subject=data.get("subject", ""),
            description=data.get("description", ""),
            result=data.get("result", ""),
            next_action_date=data.get("next_action_date"),
        )
        EventBus.publish(
            CP.INTERACTION_CREATE,
            company_id=company_id,
            payload={
                "interaction_id": interaction.id,
                "counterparty_id": interaction.counterparty_id,
                "interaction_type": interaction.interaction_type,
            },
        )
        return interaction

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, interaction_id: int, data: dict):
        """OP-CP-20."""
        interaction = Interaction.objects.select_for_update().get(
            pk=interaction_id, company_id=company_id,
        )
        for field in (
            "interaction_type", "contact_person_id", "subject",
            "description", "result", "next_action_date",
        ):
            if field in data:
                setattr(interaction, field, data[field])
        interaction.save()

        EventBus.publish(
            CP.INTERACTION_UPDATE,
            company_id=company_id,
            payload={"interaction_id": interaction.id},
        )
        return interaction