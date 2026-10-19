"""
DRF ViewSets для мобильного приложения.
Права: только аутентифицированные; данные фильтруются по company и по
hr_employee_id текущего пользователя.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.hr.api.serializers import (
    HRAbsenceSerializer, HREmployeeCertificateSerializer,
    HREmployeeSerializer, HREmployeeShortSerializer,
    HREmployeeSkillSerializer, HRTimesheetSerializer,
)
from apps.hr.models import (
    HREmployee, HREmployeeAbsence, HREmployeeCertificate,
    HREmployeeSkill, HRTimesheet,
)
from apps.hr.services import EmployeeService


class CurrentEmployeeMixin:
    """Возвращает текущего сотрудника (HREmployee) для request.user."""
    def get_current_employee(self) -> HREmployee:
        emp_id = getattr(self.request.user, "hr_employee_id", None)
        if not emp_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Пользователь не привязан к сотруднику")
        return HREmployee.objects.get(
            pk=emp_id, company_id=self.request.user.current_company_id,
        )


class ProfileViewSet(viewsets.ViewSet):
    """Профиль сотрудника и связанные данные."""
    def list(self, request):
        emp = HREmployee.objects.select_related("position").get(
            pk=request.user.hr_employee_id,
        )
        return Response({
            "employee": HREmployeeShortSerializer(emp).data,
            "skills": HREmployeeSkillSerializer(
                emp.skills.select_related("skill"), many=True,
            ).data,
            "certificates": HREmployeeCertificateSerializer(
                emp.certificates.select_related("certificate"), many=True,
            ).data,
        })


class MyAbsencesViewSet(
    CurrentEmployeeMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HRAbsenceSerializer

    def get_queryset(self):
        return HREmployeeAbsence.objects.filter(
            employee_id=self.request.user.hr_employee_id,
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        serializer.save(
            employee_id=self.request.user.hr_employee_id,
            company_id=self.request.user.current_company_id,
            status="requested",
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        absence = self.get_object()
        if absence.status != "approved":
            return Response(
                {"detail": "Можно отменить только согласованное отсутствие"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        absence.status = "cancelled"
        absence.save(update_fields=["status", "updated_at"])
        return Response(HRAbsenceSerializer(absence).data)


class MyTimesheetsViewSet(
    CurrentEmployeeMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = HRTimesheetSerializer

    def get_queryset(self):
        return HRTimesheet.objects.filter(
            employee_id=self.request.user.hr_employee_id,
            company_id=self.request.user.current_company_id,
        )

    def perform_create(self, serializer):
        serializer.save(
            employee_id=self.request.user.hr_employee_id,
            company_id=self.request.user.current_company_id,
            status="draft",
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        ts = self.get_object()
        if ts.status != "draft":
            return Response(
                {"detail": "Отправить можно только черновик"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ts.status = "submitted"
        ts.save(update_fields=["status", "updated_at"])
        return Response(HRTimesheetSerializer(ts).data)