"""
Management-команда: загружает YAML-workflow в БД.

Использование:
    python manage.py load_workflow --company=1
    python manage.py load_workflow --company=1 --module=HR
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.models import Company
from core.workflow_loader import WorkflowLoader


WORKFLOW_DIRS = {
    "HR": Path("apps/hr/workflow"),
    "TASK": Path("apps/tasks/workflow"),
    "CP": Path("apps/cp/workflow"),
    "CRM": Path("apps/crm/workflow"),
}

# Business_Roles — по одному на модуль (по имени файла)
BUSINESS_ROLES_BY_MODULE = {
    "HR": "HR_Business_Roles.yml",
    "TASK": "TASK_Business_Roles.yml",
    "CP": "CP_Business_Roles.yml",          # ← добавили
    "CRM": "CRM_Business_Roles.yml",
}


class Command(BaseCommand):
    help = "Загружает определения задач из YAML-workflow в БД"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--module", type=str, choices=list(WORKFLOW_DIRS.keys()),
        )

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(pk=options["company"])
        except Company.DoesNotExist:
            raise CommandError(f"Company {options['company']} not found")

        modules = (
            [options["module"]] if options["module"] else list(WORKFLOW_DIRS.keys())
        )

        for module in modules:
            directory = WORKFLOW_DIRS[module]
            if not directory.exists():
                self.stdout.write(
                    self.style.WARNING(f"Директория не найдена: {directory}")
                )
                continue

            business_roles_file = BUSINESS_ROLES_BY_MODULE.get(module)
            business_roles_path = (
                directory / business_roles_file if business_roles_file else None
            )

            loader = WorkflowLoader(
                company_id=company.id,
                module=module,
                business_roles_path=business_roles_path,
            )

            for path in sorted(directory.glob("*_Process_Workflow.yml")):
                self.stdout.write(f"Загрузка {path} ...")
                stats = loader.load_file(path)
                self.stdout.write(self.style.SUCCESS(
                    f"  created={stats['created']}, "
                    f"updated={stats['updated']}, "
                    f"transitions={stats['transitions']}"
                ))

        self.stdout.write(self.style.SUCCESS("Workflow загружен"))