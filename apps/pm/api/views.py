"""
DRF ViewSets PM. Все запросы фильтруются по активной компании пользователя.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.pm.api.serializers import (
    BudgetItemSerializer, BudgetSerializer,
    ChangeRequestSerializer, MilestoneSerializer,
    PhaseSerializer, ProjectCreateSerializer,
    ProjectDetailSerializer, ProjectListSerializer,
    ReportSerializer, ResourceNeedSerializer,
    RiskSerializer, StatusHistorySerializer,
    TaskDependencySerializer, TaskSerializer,
)
from apps.pm.models import (
    Budget, BudgetItem, ChangeRequest, Milestone, Phase, Project,
    Report, ResourceNeed, Risk, StatusHistory, Task, TaskDependency,
)
from apps.pm.services import (
    BudgetItemService, BudgetService,
    ChangeRequestService, MilestoneService,
    PhaseService, ProjectService,
    ReportService, ResourceNeedService,
    RiskService, StatusHistoryService,
    TaskDependencyService, TaskService,
)


class CompanyScopedMixin:
    def get_company_id(self) -> int:
        cid = getattr(self.request.user, "current_company_id", None)
        if not cid:
            raise PermissionDenied("Компания не выбрана")
        return cid

    def get_employee_id(self) -> int | None:
        return getattr(self.request.user, "hr_employee_id", None)


# ============================================================
# Проекты
# ============================================================

class ProjectViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Project.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            s = self.request.query_params.get("status")
            if s:
                qs = qs.filter(status=s)
            c = self.request.query_params.get("customer_id")
            if c:
                qs = qs.filter(customer_id=c)
        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProjectCreateSerializer
        return ProjectListSerializer

    def perform_create(self, serializer):
        serializer.instance = ProjectService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    def perform_update(self, serializer):
        serializer.instance = ProjectService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        p = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            raise ValidationError("status обязателен")
        try:
            p = ProjectService.update_status(
                company_id=self.get_company_id(),
                project_id=p.id, new_status=new_status,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProjectDetailSerializer(p).data)

    @action(detail=True, methods=["post"], url_path="assign-manager")
    def assign_manager(self, request, pk=None):
        p = self.get_object()
        eid = request.data.get("employee_id")
        if not eid:
            raise ValidationError("employee_id обязателен")
        p = ProjectService.assign_manager(
            company_id=self.get_company_id(),
            project_id=p.id, employee_id=int(eid),
        )
        return Response(ProjectDetailSerializer(p).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        p = self.get_object()
        try:
            p = ProjectService.complete(
                company_id=self.get_company_id(), project_id=p.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProjectDetailSerializer(p).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        p = self.get_object()
        try:
            p = ProjectService.cancel(
                company_id=self.get_company_id(), project_id=p.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ProjectDetailSerializer(p).data)


# ============================================================
# Этапы и вехи
# ============================================================

class PhaseViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = PhaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Phase.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("project", "order")

    def perform_create(self, serializer):
        serializer.instance = PhaseService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = PhaseService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        phase = self.get_object()
        try:
            phase = PhaseService.complete(
                company_id=self.get_company_id(), phase_id=phase.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(PhaseSerializer(phase).data)


class MilestoneViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = MilestoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Milestone.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("milestone_date")

    def perform_create(self, serializer):
        serializer.instance = MilestoneService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = MilestoneService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"])
    def achieve(self, request, pk=None):
        m = self.get_object()
        m = MilestoneService.achieve(
            company_id=self.get_company_id(), milestone_id=m.id,
        )
        return Response(MilestoneSerializer(m).data)


# ============================================================
# Задачи и зависимости
# ============================================================

class TaskViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Task.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        ph = self.request.query_params.get("phase_id")
        if ph:
            qs = qs.filter(phase_id=ph)
        a = self.request.query_params.get("assignee_id")
        if a:
            qs = qs.filter(assignee_employee_id=a)
        return qs.order_by("project", "priority", "planned_start_date")

    def perform_create(self, serializer):
        serializer.instance = TaskService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = TaskService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        t = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            raise ValidationError("status обязателен")
        completion = request.data.get("completion_percent")
        try:
            t = TaskService.update_status(
                company_id=self.get_company_id(),
                task_id=t.id, new_status=new_status,
                completion_percent=completion,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TaskSerializer(t).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        t = self.get_object()
        eid = request.data.get("employee_id")
        if not eid:
            raise ValidationError("employee_id обязателен")
        t = TaskService.assign(
            company_id=self.get_company_id(),
            task_id=t.id, employee_id=int(eid),
        )
        return Response(TaskSerializer(t).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        t = self.get_object()
        try:
            t = TaskService.complete(
                company_id=self.get_company_id(), task_id=t.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TaskSerializer(t).data)


class TaskDependencyViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TaskDependencySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskDependency.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = TaskDependencyService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        TaskDependencyService.delete(
            company_id=self.get_company_id(), dependency_id=instance.id,
        )


# ============================================================
# Ресурсные потребности
# ============================================================

class ResourceNeedViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ResourceNeedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ResourceNeed.objects.filter(company_id=self.get_company_id())
        t = self.request.query_params.get("task_id")
        if t:
            qs = qs.filter(task_id=t)
        return qs

    def perform_create(self, serializer):
        serializer.instance = ResourceNeedService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = ResourceNeedService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"], url_path="send-to-aps")
    def send_to_aps(self, request, pk=None):
        rn = self.get_object()
        rn = ResourceNeedService.send_to_aps(
            company_id=self.get_company_id(), resource_need_id=rn.id,
        )
        return Response(ResourceNeedSerializer(rn).data)


# ============================================================
# Бюджет
# ============================================================

class BudgetViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Budget.objects.filter(company_id=self.get_company_id()).prefetch_related("items")
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs

    def perform_create(self, serializer):
        serializer.instance = BudgetService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = BudgetService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        b = self.get_object()
        eid = self.get_employee_id()
        if not eid:
            raise ValidationError("Пользователь не привязан к сотруднику")
        try:
            b = BudgetService.approve(
                company_id=self.get_company_id(),
                budget_id=b.id, approver_employee_id=eid,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(BudgetSerializer(b).data)


class BudgetItemViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BudgetItem.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = BudgetItemService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = BudgetItemService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


# ============================================================
# Риски и изменения
# ============================================================

class RiskViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = RiskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Risk.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("-severity")

    def perform_create(self, serializer):
        serializer.instance = RiskService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = RiskService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


class ChangeRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ChangeRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ChangeRequest.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("-requested_at")

    def perform_create(self, serializer):
        serializer.instance = ChangeRequestService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )

    def perform_update(self, serializer):
        serializer.instance = ChangeRequestService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
            actor_employee_id=self.get_employee_id(),
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        cr = self.get_object()
        eid = self.get_employee_id()
        if not eid:
            raise ValidationError("Пользователь не привязан к сотруднику")
        try:
            cr = ChangeRequestService.approve(
                company_id=self.get_company_id(),
                change_request_id=cr.id, approver_employee_id=eid,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(ChangeRequestSerializer(cr).data)


# ============================================================
# Отчётность
# ============================================================

class StatusHistoryViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StatusHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = StatusHistory.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("-changed_at")

    def perform_create(self, serializer):
        serializer.instance = StatusHistoryService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            actor_employee_id=self.get_employee_id(),
        )


class ReportViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Report.objects.filter(company_id=self.get_company_id())
        p = self.request.query_params.get("project_id")
        if p:
            qs = qs.filter(project_id=p)
        return qs.order_by("-report_date")

    def perform_create(self, serializer):
        serializer.instance = ReportService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"], url_path="send-to-orchestrator")
    def send_to_orchestrator(self, request, pk=None):
        r = self.get_object()
        r = ReportService.send_to_orchestrator(
            company_id=self.get_company_id(), report_id=r.id,
        )
        return Response(ReportSerializer(r).data)