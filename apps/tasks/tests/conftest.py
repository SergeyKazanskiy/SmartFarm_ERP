import pytest
from django.contrib.auth import get_user_model

from apps.companies.models import Company


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Co", short_name="TC")


@pytest.fixture
def user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="hr1", email="hr@test.co", password="pass12345",
        hr_employee_id=1,
    )
    u.companies.add(company)
    u.current_company = company
    u.save()
    return u