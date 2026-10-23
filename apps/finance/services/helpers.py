import uuid
from decimal import Decimal


def gen_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# Коды счетов по умолчанию для авто-проводок (можно переопределить в settings).
DEFAULT_AR_ACCOUNT_CODE = "62"    # Расчёты с покупателями
DEFAULT_AP_ACCOUNT_CODE = "60"    # Расчёты с поставщиками
DEFAULT_BANK_ACCOUNT_CODE = "51"  # Денежные средства на счетах
DEFAULT_CASH_ACCOUNT_CODE = "50"  # Касса
DEFAULT_REVENUE_ACCOUNT_CODE = "70"    # Выручка
DEFAULT_COGS_ACCOUNT_CODE = "90"       # Себестоимость


def find_account_by_code(company_id: int, account_code: str):
    """Ищет FinAccount по коду в плане счетов компании."""
    from apps.finance.models import FinAccount
    return FinAccount.objects.filter(
        company_id=company_id, account_code=account_code,
    ).first()