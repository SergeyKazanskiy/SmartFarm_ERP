from rest_framework.routers import DefaultRouter

from apps.production.api.views import (
    BomItemViewSet, BomViewSet, MaterialPriceHistoryViewSet,
    OperationDefinitionViewSet, OperationExecutionViewSet,
    ProductionOrderViewSet, QualityPointViewSet,
    RoutingViewSet, TechnologyViewSet,
    WorkCenterViewSet, WorkOrderViewSet,
)

router = DefaultRouter()
router.register("production/technologies", TechnologyViewSet, basename="prod-technologies")
router.register("production/work-centers", WorkCenterViewSet, basename="prod-work-centers")
router.register("production/routings", RoutingViewSet, basename="prod-routings")
router.register("production/operations", OperationDefinitionViewSet, basename="prod-operations")
router.register("production/quality-points", QualityPointViewSet, basename="prod-quality-points")
router.register("production/boms", BomViewSet, basename="prod-boms")
router.register("production/bom-items", BomItemViewSet, basename="prod-bom-items")
router.register("production/material-price-history", MaterialPriceHistoryViewSet, basename="prod-material-price-history")
router.register("production/orders", ProductionOrderViewSet, basename="prod-orders")
router.register("production/work-orders", WorkOrderViewSet, basename="prod-work-orders")
router.register("production/executions", OperationExecutionViewSet, basename="prod-executions")

urlpatterns = router.urls