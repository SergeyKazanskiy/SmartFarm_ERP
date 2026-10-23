import uuid
from decimal import Decimal, ROUND_HALF_UP


def gen_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def calc_line_total(
    quantity, unit_price, discount_percent=None,
) -> Decimal:
    """
    quantity × unit_price × (1 − discount/100), округление до 4 знаков.
    Соответствует SQL OP-SALES-10 / OP-SALES-14.
    """
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    discount = Decimal(str(discount_percent or 0))
    total = qty * price * (Decimal("1") - discount / Decimal("100"))
    return total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)