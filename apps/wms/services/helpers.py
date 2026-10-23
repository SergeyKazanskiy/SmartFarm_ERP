import uuid
from decimal import Decimal, ROUND_HALF_UP


def gen_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def calc_moving_average(
    old_qty: Decimal,
    old_cost: Decimal | None,
    new_qty: Decimal,
    new_cost: Decimal | None,
) -> Decimal | None:
    """
    Скользящее среднее: (old_qty × old_cost + new_qty × new_cost) / (old_qty + new_qty).
    Возвращает None, если себестоимость не задана ни для одной из сторон.
    """
    total_qty = (old_qty or Decimal("0")) + (new_qty or Decimal("0"))
    if total_qty <= 0:
        return new_cost if new_cost is not None else old_cost

    old_val = (old_qty or Decimal("0")) * (old_cost or Decimal("0"))
    new_val = (new_qty or Decimal("0")) * (new_cost or Decimal("0"))

    result = (old_val + new_val) / total_qty
    return result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def resolve_inventory(
    company_id: int,
    material_id: int,
    location_id: int,
    lot_id: int | None = None,
    serial_id: int | None = None,
):
    """
    Находит или создаёт Inventory по уникальному ключу
    (company, material, location, lot, serial).
    """
    from apps.wms.models import Inventory

    inv, _ = Inventory.objects.select_for_update().get_or_create(
        company_id=company_id,
        material_id=material_id,
        location_id=location_id,
        lot_id=lot_id,
        serial_id=serial_id,
        defaults={"code": gen_code("INV"), "quantity": Decimal("0")},
    )
    return inv