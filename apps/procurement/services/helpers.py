import uuid
from decimal import Decimal, ROUND_HALF_UP


def gen_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def calc_line_total(quantity, unit_price) -> Decimal:
    """quantity × unit_price с округлением до 4 знаков."""
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    return (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)