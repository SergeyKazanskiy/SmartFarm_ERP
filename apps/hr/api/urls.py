from rest_framework.routers import DefaultRouter

from apps.hr.api.views import (
    MyAbsencesViewSet, MyTimesheetsViewSet, ProfileViewSet,
)

router = DefaultRouter()
router.register("hr/profile", ProfileViewSet, basename="hr-profile")
router.register("hr/absences", MyAbsencesViewSet, basename="hr-absences")
router.register("hr/timesheets", MyTimesheetsViewSet, basename="hr-timesheets")

urlpatterns = router.urls