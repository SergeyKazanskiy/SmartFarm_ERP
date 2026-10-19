"""
DRF ViewSets для мобильного приложения (React Native).
Все запросы фильтруются по company текущего пользователя.
"""
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.event_bus import EventBus
from core.events import TaskEvents as TE

from apps.tasks.api.serializers import (
    TaskCommentSerializer, TaskDetailSerializer, TaskListSerializer,
    TaskNotificationSerializer, TaskPhotoSerializer, TaskTimeTrackingSerializer,
)
from apps.tasks.models import (
    TaskComment, TaskNotification, TaskPhoto, TaskTask, TaskTimeTracking,
)

# ---------- Базовый ViewSet ----------
class CompanyScopedViewSet(viewsets.GenericViewSet):
    """Базовый ViewSet: фильтрует по company и hr_employee_id."""

    def get_company_id(self) -> int:
        company_id = getattr(self.request.user, "current_company_id", None)
        if not company_id:
            raise PermissionDenied("Компания не выбрана")
        return company_id

    def get_employee_id(self) -> int:
        emp_id = getattr(self.request.user, "hr_employee_id", None)
        if not emp_id:
            raise PermissionDenied("Пользователь не привязан к сотруднику")
        return emp_id

# ---------- ViewSet для моих задач ----------
class MyTasksViewSet(
    CompanyScopedViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/v1/tasks/my/           — список моих задач
    GET /api/v1/tasks/my/{id}/      — детали задачи
    POST /api/v1/tasks/my/{id}/start/
    POST /api/v1/tasks/my/{id}/complete/
    POST /api/v1/tasks/my/{id}/hold/
    POST /api/v1/tasks/my/{id}/resume/
    POST /api/v1/tasks/my/{id}/comments/    — добавить комментарий
    GET  /api/v1/tasks/my/{id}/comments/    — список комментариев
    POST /api/v1/tasks/my/{id}/time/        — добавить учёт времени
    POST /api/v1/tasks/my/{id}/photos/      — загрузить фото
    """
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        emp_id = self.get_employee_id()
        company_id = self.get_company_id()
        return (
            TaskTask.objects
            .filter(company_id=company_id)
            .filter(
                Q(assignments__employee_id=emp_id)
                | Q(assigned_role="", status="created")
            )
            .distinct()
            .select_related("definition")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TaskDetailSerializer
        return TaskListSerializer

    # ---------- Действия ----------

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.status not in ("assigned", "created"):
            return Response(
                {"detail": "Начать можно только назначенную или созданную задачу"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "in_progress"
        task.actual_start = timezone_now()
        task.save(update_fields=["status", "actual_start", "updated_at"])

        EventBus.publish(
            TE.TASK_START,
            company_id=task.company_id,
            payload={"task_id": task.id, "employee_id": self.get_employee_id()},
        )
        return Response(TaskDetailSerializer(task).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.status != "in_progress":
            return Response(
                {"detail": "Завершить можно только задачу в работе"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "completed"
        task.completion_percent = 100
        task.actual_finish = timezone_now()
        task.save(update_fields=[
            "status", "completion_percent", "actual_finish", "updated_at",
        ])

        EventBus.publish(
            TE.TASK_COMPLETE,
            company_id=task.company_id,
            payload={"task_id": task.id, "employee_id": self.get_employee_id()},
        )
        return Response(TaskDetailSerializer(task).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        task = self.get_object()
        if task.status != "in_progress":
            return Response({"detail": "Неверный статус"}, status=400)
        task.status = "on_hold"
        task.save(update_fields=["status", "updated_at"])
        EventBus.publish(TE.TASK_HOLD_TOGGLE, company_id=task.company_id,
                         payload={"task_id": task.id, "action": "hold"})
        return Response(TaskDetailSerializer(task).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        task = self.get_object()
        if task.status != "on_hold":
            return Response({"detail": "Неверный статус"}, status=400)
        task.status = "in_progress"
        task.save(update_fields=["status", "updated_at"])
        EventBus.publish(TE.TASK_HOLD_TOGGLE, company_id=task.company_id,
                         payload={"task_id": task.id, "action": "resume"})
        return Response(TaskDetailSerializer(task).data)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        task = self.get_object()
        if request.method == "GET":
            qs = task.comments.all().order_by("-created_at")
            return Response(TaskCommentSerializer(qs, many=True).data)

        serializer = TaskCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(
            task=task,
            company_id=task.company_id,
            employee_id=self.get_employee_id(),
        )
        EventBus.publish(
            TE.COMMENT_SAVE, company_id=task.company_id,
            payload={"task_id": task.id, "comment_id": comment.id},
        )
        return Response(TaskCommentSerializer(comment).data, status=201)

    @action(detail=True, methods=["get", "post"])
    def time(self, request, pk=None):
        task = self.get_object()
        if request.method == "GET":
            qs = task.time_tracking.all().order_by("-date_logged")
            return Response(TaskTimeTrackingSerializer(qs, many=True).data)

        serializer = TaskTimeTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(
            task=task,
            company_id=task.company_id,
            employee_id=self.get_employee_id(),
        )
        EventBus.publish(
            TE.TIME_TRACKING_SAVE, company_id=task.company_id,
            payload={"task_id": task.id, "entry_id": entry.id, "hours": float(entry.hours)},
        )
        return Response(TaskTimeTrackingSerializer(entry).data, status=201)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def photos(self, request, pk=None):
        task = self.get_object()
        serializer = TaskPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(
            task=task,
            company_id=task.company_id,
            employee_id=self.get_employee_id(),
        )
        EventBus.publish(
            TE.PHOTO_SAVE, company_id=task.company_id,
            payload={"task_id": task.id, "photo_id": photo.id},
        )
        return Response(TaskPhotoSerializer(photo).data, status=201)

# ---------- ViewSet для моих уведомлений ----------
class MyNotificationsViewSet(
    CompanyScopedViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/v1/notifications/          — мои уведомления
    POST /api/v1/notifications/{id}/read/ — отметить прочитанным
    POST /api/v1/notifications/read-all/  — отметить все прочитанными
    """
    serializer_class = TaskNotificationSerializer

    def get_queryset(self):
        return TaskNotification.objects.filter(
            company_id=self.get_company_id(),
            employee_id=self.get_employee_id(),
        ).select_related("task").order_by("-sent_at")

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.read_at = timezone_now()
        n.save(update_fields=["is_read", "read_at"])
        return Response(TaskNotificationSerializer(n).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone_now(),
        )
        return Response({"status": "ok"})


# Хелпер
from django.utils import timezone as _tz
def timezone_now():
    return _tz.now()