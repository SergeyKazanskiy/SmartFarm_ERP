import uuid
from decimal import Decimal, ROUND_HALF_UP


def gen_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def calc_line_total(quantity, unit_price) -> Decimal:
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    return (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def validate_json_list(value, field_name: str) -> list:
    """Проверяет, что JSON-поле — список. Возвращает [] для None."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} должен быть списком")
    return value


def has_failed_quality(quality_results_json: list) -> bool:
    """Возвращает True, если хоть один is_passed=false."""
    if not quality_results_json:
        return False
    for item in quality_results_json:
        if isinstance(item, dict) and item.get("is_passed") is False:
            return True
    return False