"""
Регистрация всех ModelAdmin HR-модуля.
Разбито по файлам для читаемости.
"""
from apps.hr.admin.absences import *      # noqa: F401, F403
from apps.hr.admin.employees import *     # noqa: F401, F403
from apps.hr.admin.references import *    # noqa: F401, F403
from apps.hr.admin.safety import *        # noqa: F401, F403
from apps.hr.admin.skills import *        # noqa: F401, F403
from apps.hr.admin.timesheets import *    # noqa: F401, F403