import pytest
from django.db import IntegrityError

from apps.cp.models import Address, ContactPerson


@pytest.mark.django_db
def test_code_unique_per_company(company, cp_type):
    from apps.cp.models import CounterpartyType
    CounterpartyType.objects.create(company=company, code="CPT-001", name="A")
    with pytest.raises(IntegrityError):
        CounterpartyType.objects.create(company=company, code="CPT-001", name="B")


@pytest.mark.django_db
def test_cascade_delete_contact(counterparty):
    contact = ContactPerson.objects.create(
        company=counterparty.company, code="CONT-001",
        counterparty=counterparty, last_name="Иванов",
    )
    counterparty.delete()
    assert not ContactPerson.objects.filter(pk=contact.pk).exists()


@pytest.mark.django_db
def test_cascade_delete_address(counterparty):
    addr = Address.objects.create(
        company=counterparty.company, code="ADDR-001",
        counterparty=counterparty, city="Киев",
    )
    counterparty.delete()
    assert not Address.objects.filter(pk=addr.pk).exists()


@pytest.mark.django_db
def test_protect_counterparty_type(counterparty, cp_type):
    """Удалить тип, на котором есть контрагенты, нельзя."""
    from django.db.models import ProtectedError
    with pytest.raises(ProtectedError):
        cp_type.delete()