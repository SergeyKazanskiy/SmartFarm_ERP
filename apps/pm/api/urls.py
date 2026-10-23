from rest_framework.routers import DefaultRouter

from apps.pm.api.views import (
    BudgetItemViewSet, BudgetViewSet,
    ChangeRequestViewSet, MilestoneViewSet,
    PhaseViewSet, ProjectViewSet,
    ReportViewSet, ResourceNeedViewSet,
    RiskViewSet, StatusHistoryViewSet,
    TaskDependencyViewSet, TaskViewSet,
)

router = DefaultRouter()
router.register("pm/projects", ProjectViewSet, basename="pm-projects")
router.register("pm/phases", PhaseViewSet, basename="pm-phases")
router.register("pm/milestones", MilestoneViewSet, basename="pm-milestones")
router.register("pm/tasks", TaskViewSet, basename="pm-tasks")
router.register("pm/task-dependencies", TaskDependencyViewSet, basename="pm-task-dependencies")
router.register("pm/resource-needs", ResourceNeedViewSet, basename="pm-resource-needs")
router.register("pm/budgets", BudgetViewSet, basename="pm-budgets")
router.register("pm/budget-items", BudgetItemViewSet, basename="pm-budget-items")
router.register("pm/risks", RiskViewSet, basename="pm-risks")
router.register("pm/change-requests", ChangeRequestViewSet, basename="pm-change-requests")
router.register("pm/status-history", StatusHistoryViewSet, basename="pm-status-history")
router.register("pm/reports", ReportViewSet, basename="pm-reports")

urlpatterns = router.urls