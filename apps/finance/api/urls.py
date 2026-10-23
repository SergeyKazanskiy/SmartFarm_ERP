from rest_framework.routers import DefaultRouter

from apps.finance.api.views import (
    BankAccountViewSet, BudgetItemViewSet, BudgetViewSet,
    CashAccountViewSet, CostCenterViewSet, ExchangeRateViewSet,
    FinAccountViewSet, FinancialIndicatorViewSet,
    FinancialPeriodViewSet, FinancialProjectViewSet,
    FinancialTransactionViewSet, InvoiceLineViewSet, InvoiceViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register("finance/accounts", FinAccountViewSet, basename="fin-accounts")
router.register("finance/cost-centers", CostCenterViewSet, basename="fin-cost-centers")
router.register("finance/projects", FinancialProjectViewSet, basename="fin-projects")
router.register("finance/cash-accounts", CashAccountViewSet, basename="fin-cash-accounts")
router.register("finance/bank-accounts", BankAccountViewSet, basename="fin-bank-accounts")
router.register("finance/exchange-rates", ExchangeRateViewSet, basename="fin-exchange-rates")
router.register("finance/budgets", BudgetViewSet, basename="fin-budgets")
router.register("finance/budget-items", BudgetItemViewSet, basename="fin-budget-items")
router.register("finance/invoices", InvoiceViewSet, basename="fin-invoices")
router.register("finance/invoice-lines", InvoiceLineViewSet, basename="fin-invoice-lines")
router.register("finance/payments", PaymentViewSet, basename="fin-payments")
router.register("finance/transactions", FinancialTransactionViewSet, basename="fin-transactions")
router.register("finance/periods", FinancialPeriodViewSet, basename="fin-periods")
router.register("finance/indicators", FinancialIndicatorViewSet, basename="fin-indicators")

urlpatterns = router.urls