from rest_framework.routers import DefaultRouter

from apps.tasks.api.views import MyNotificationsViewSet, MyTasksViewSet

router = DefaultRouter()
router.register("tasks/my", MyTasksViewSet, basename="my-tasks")
router.register("notifications", MyNotificationsViewSet, basename="my-notifications")

urlpatterns = router.urls