"""
Подписчики Finance-модуля на события других модулей.

Реализовано:
- Sales.invoice.pay → создать fin_payment (completed) + автопроводка.
- Sales.order.completed → создать fin_invoice (AR) на сумму заказа.
- CP.blacklist.add → пометить все открытые fin_invoice контрагента как overdue.

Заглушки:
- PM.budget.approve → создать fin_budget (когда свяжем PM-бюджет с FIN-бюджетом).
- HR.timesheet.review (approved) → создать fin_invoice (AP) на зарплату.
- Procurement.order.received → создать fin_invoice (AP).
"""
import logging

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.event_bus import DomainEvent, EventBus

from apps.finance.models import Invoice, Payment
from apps.finance.services.helpers import gen_code
from apps.finance.services.payments import PaymentService

logger = logging.getLogger(__name__)


# ============================================================
# Sales → Finance
# ============================================================

@EventBus.subscribe("Sales.order.create")
@transaction.atomic
def on_sales_order_create(event: DomainEvent) -> None:
    """
    Заказ клиента создан → создать черновик AR-счёта на сумму заказа.
    """
    order_id = event.payload.get("order_id")
    customer_id = event.payload.get("customer_id")
    if not order_id or not customer_id:
        return

    # Резолвим заказ из Sales, чтобы взять customer.counterparty_id и total_amount
    from apps.sales.models import Order
    order = Order.objects.filter(
        pk=order_id, company_id=event.company_id,
    ).first()
    if order is None:
        return

    # Проверка идемпотентности: один AR-счёт на заказ
    if Invoice.objects.filter(
        company_id=event.company_id,
        source_object_type="sales_order",
        source_object_id=order.id,
        invoice_type="AR",
    ).exists():
        return

    Invoice.objects.create(
        company_id=event.company_id,
        code=gen_code("FINV"),
        invoice_type="AR",
        counterparty_id=order.customer.counterparty_id,
        contract_id=None,
        source_object_type="sales_order",
        source_object_id=order.id,
        invoice_number=f"AR-{order.order_number}",
        invoice_date=order.order_date,
        due_date=order.expected_ship_date,
        amount=order.total_amount or Decimal("0"),
        currency_id=order.currency_id,
        status="draft",
    )
    logger.info(
        "FIN: создан AR-счёт по заказу %s (company=%s)",
        order.id, event.company_id,
    )


@EventBus.subscribe("Sales.invoice.pay")
@transaction.atomic
def on_sales_invoice_pay(event: DomainEvent) -> None:
    """
    Sales.Invoice оплачен → создать fin_payment (completed) и провести его.
    Автоматически создастся проводка Дт «Денежные средства» — Кт «Расчёты с покупателями».
    """
    order_id = event.payload.get("order_id")
    paid_amount = event.payload.get("paid_amount")
    if not order_id or not paid_amount:
        return

    # Найти наш AR-счёт, связанный с этим Sales-заказом
    inv = Invoice.objects.filter(
        company_id=event.company_id,
        source_object_type="sales_order",
        source_object_id=order_id,
        invoice_type="AR",
    ).first()
    if inv is None:
        return

    payment = Payment.objects.create(
        company_id=event.company_id,
        code=gen_code("PAY"),
        invoice=inv,
        bank_account=None,
        cash_account=None,
        payment_status="planned",
        payment_date=timezone.now(),
        amount=Decimal(str(paid_amount)),
    )
    PaymentService.complete(
        company_id=event.company_id, payment_id=payment.id,
    )


# ============================================================
# CP → Finance
# ============================================================

@EventBus.subscribe("CP.blacklist.add")
@transaction.atomic
def on_cp_blacklist_add(event: DomainEvent) -> None:
    """
    Контрагент попал в чёрный список → все открытые счета становятся overdue.
    """
    counterparty_id = event.payload.get("counterparty_id")
    if not counterparty_id:
        return

    affected = Invoice.objects.filter(
        company_id=event.company_id,
        counterparty_id=counterparty_id,
        status__in=["draft", "issued", "partially_paid"],
    ).update(status="overdue")

    logger.info(
        "FIN: blacklisted counterparty %s → %d invoices overdue",
        counterparty_id, affected,
    )


# ============================================================
# Заглушки для будущих модулей
# ============================================================

# @EventBus.subscribe("PM.budget.approve")
# def on_pm_budget_approve(event: DomainEvent) -> None:
#     """PM-бюджет утверждён → создать FIN-бюджет для управленческого учёта."""
#     ...

# @EventBus.subscribe("HR.timesheet.review")
# def on_hr_timesheet_approved(event: DomainEvent) -> None:
#     """Табель утверждён → создать AP-счёт на зарплату."""
#     ...