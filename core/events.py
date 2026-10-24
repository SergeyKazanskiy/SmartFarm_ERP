"""
Реестр имён событий ERP.
Соглашение: <MODULE>.<entity>.<action> в camelCase, как в YAML-файлах.
"""


class HREvents:
    """События HR-модуля (из HR_Business_Roles.yml)."""
    POSITION_CATEGORY_CREATE = "HR.positionCategory.create"
    POSITION_SAVE = "HR.position.save"
    WORK_SCHEDULE_SAVE = "HR.workSchedule.save"
    SKILL_GROUP_CREATE = "HR.skillGroup.create"
    SKILL_SAVE = "HR.skill.save"
    QUALIFICATION_CREATE = "HR.qualification.create"
    CERTIFICATE_CREATE = "HR.certificate.create"
    ABSENCE_TYPE_CREATE = "HR.absenceType.create"

    EMPLOYEE_HIRE = "HR.employee.hire"
    EMPLOYEE_TRANSFER = "HR.employee.transfer"
    EMPLOYEE_START_LEAVE = "HR.employee.startLeave"
    EMPLOYEE_END_LEAVE = "HR.employee.endLeave"
    EMPLOYEE_SUSPEND = "HR.employee.suspend"
    EMPLOYEE_DISMISS = "HR.employee.dismiss"
    EMPLOYEE_DOCUMENT_ATTACH = "HR.employeeDocument.attach"

    EMPLOYEE_SKILL_SELF_ASSESS = "HR.employeeSkill.selfAssess"
    EMPLOYEE_SKILL_CONFIRM = "HR.employeeSkill.confirm"
    EMPLOYEE_COMPETENCY_SCORE_CREATE = "HR.employeeCompetencyScore.create"
    EMPLOYEE_QUALIFICATION_ASSIGN = "HR.employeeQualification.assign"
    EMPLOYEE_QUALIFICATION_EXTEND = "HR.employeeQualification.extend"

    EMPLOYEE_CERTIFICATE_ISSUE = "HR.employeeCertificate.issue"
    EMPLOYEE_CERTIFICATE_EXTEND = "HR.employeeCertificate.extend"
    MEDICAL_CHECK_CREATE = "HR.medicalCheck.create"
    DRIVING_LICENSE_CREATE = "HR.drivingLicense.create"
    DRIVING_LICENSE_EXTEND = "HR.drivingLicense.extend"

    EMPLOYEE_ABSENCE_REQUEST = "HR.employeeAbsence.request"
    EMPLOYEE_ABSENCE_REVIEW = "HR.employeeAbsence.review"
    EMPLOYEE_ABSENCE_CANCEL = "HR.employeeAbsence.cancel"

    TIMESHEET_CREATE = "HR.timesheet.create"
    TIMESHEET_UPDATE = "HR.timesheet.update"
    TIMESHEET_SUBMIT = "HR.timesheet.submit"
    TIMESHEET_REVIEW = "HR.timesheet.review"


class TaskEvents:
    """События TASK-модуля."""
    TASK_SAVE = "Task.task.save"
    TASK_UPDATE_STATUS = "Task.task.updateStatus"
    TASK_ASSIGN = "Task.task.assign"
    TASK_START = "Task.task.start"
    TASK_COMPLETE = "Task.task.complete"
    TASK_CANCEL = "Task.task.cancel"
    TASK_HOLD_TOGGLE = "Task.task.holdToggle"
    TASK_UPDATE_COMPLETION = "Task.task.updateCompletion"

    COMMENT_SAVE = "Task.comment.save"
    PHOTO_SAVE = "Task.photo.save"
    TIME_TRACKING_SAVE = "Task.timeTracking.save"


class CPEvents:
    """События CP-модуля (из CP_Business_Roles.yml)."""
    COUNTERPARTY_TYPE_SAVE = "CP.counterpartyType.save"
    CATEGORY_SAVE = "CP.category.save"
    COUNTERPARTY_SAVE = "CP.counterparty.save"
    COUNTERPARTY_UPDATE_STATUS = "CP.counterparty.updateStatus"
    COUNTERPARTY_ASSIGN_RESPONSIBLE = "CP.counterparty.assignResponsible"
    CONTACT_PERSON_SAVE = "CP.contactPerson.save"
    CONTACT_PERSON_DELETE = "CP.contactPerson.delete"
    BANK_ACCOUNT_SAVE = "CP.bankAccount.save"
    BANK_ACCOUNT_DELETE = "CP.bankAccount.delete"
    ADDRESS_SAVE = "CP.address.save"
    ADDRESS_DELETE = "CP.address.delete"
    RATING_CREATE = "CP.rating.create"
    INTERACTION_CREATE = "CP.interaction.create"
    INTERACTION_UPDATE = "CP.interaction.update"
    CONTRACT_SAVE = "CP.contract.save"
    CONTRACT_ACTIVATE = "CP.contract.activate"
    CONTRACT_TERMINATE = "CP.contract.terminate"
    BLACKLIST_ADD = "CP.blacklist.add"
    BLACKLIST_REMOVE = "CP.blacklist.remove"
    ATTACHMENT_CREATE = "CP.attachment.create"
    ATTACHMENT_DELETE = "CP.attachment.delete"


class ProductionEvents:
    """События Production-модуля (из Production_Business_Roles.yml)."""
    # Технологии, маршруты, центры, операции
    TECHNOLOGY_CREATE = "Production.technology.create"
    TECHNOLOGY_RENAME = "Production.technology.rename"
    ROUTING_CREATE = "Production.routing.create"
    ROUTING_UPDATE = "Production.routing.update"
    WORK_CENTER_CREATE = "Production.workCenter.create"
    WORK_CENTER_RENAME = "Production.workCenter.rename"
    OPERATION_CREATE = "Production.operation.create"
    OPERATION_UPDATE_PARAMETERS = "Production.operation.updateParameters"
    OPERATION_UPDATE_RESOURCES = "Production.operation.updateResources"
    OPERATION_MOVE_WORK_CENTER = "Production.operation.moveWorkCenter"
    OPERATION_REORDER = "Production.operation.reorder"
    OPERATION_RENAME = "Production.operation.rename"
    QUALITY_POINT_CREATE = "Production.qualityPoint.create"
    QUALITY_POINT_RENAME = "Production.qualityPoint.rename"

    # BOM
    BOM_CREATE = "Production.bom.create"
    BOM_UPDATE = "Production.bom.update"
    BOM_ITEM_CREATE = "Production.bomItem.create"
    BOM_ITEM_UPDATE_QUANTITY = "Production.bomItem.updateQuantity"
    BOM_ITEM_REPLACE_MATERIAL = "Production.bomItem.replaceMaterial"
    BOM_ITEM_UPDATE_COST = "Production.bomItem.updateCost"

    # Производственный заказ
    PRODUCTION_ORDER_CREATE = "Production.productionOrder.create"
    PRODUCTION_ORDER_CONFIRM = "Production.productionOrder.confirm"
    PRODUCTION_ORDER_UPDATE_PLAN = "Production.productionOrder.updatePlan"
    PRODUCTION_ORDER_UPDATE_BOM_ROUTING = "Production.productionOrder.updateBomRouting"
    PRODUCTION_ORDER_START = "Production.productionOrder.start"
    PRODUCTION_ORDER_COMPLETE = "Production.productionOrder.complete"
    PRODUCTION_ORDER_CANCEL = "Production.productionOrder.cancel"

    # Наряд
    WORK_ORDER_CREATE = "Production.workOrder.create"
    WORK_ORDER_START = "Production.workOrder.start"
    WORK_ORDER_HOLD = "Production.workOrder.hold"
    WORK_ORDER_RESUME = "Production.workOrder.resume"
    WORK_ORDER_COMPLETE = "Production.workOrder.complete"
    WORK_ORDER_CANCEL = "Production.workOrder.cancel"
    WORK_ORDER_UPDATE_SCHEDULE = "Production.workOrder.updateSchedule"
    WORK_ORDER_REGISTER_MATERIALS = "Production.workOrder.registerMaterials"

    # Выполнение операции
    EXECUTION_START = "Production.operationExecution.start"
    EXECUTION_ASSIGN_EMPLOYEE = "Production.operationExecution.assignEmployee"
    EXECUTION_MOVE_WORK_CENTER = "Production.operationExecution.moveWorkCenter"
    EXECUTION_RECORD_MEASUREMENTS = "Production.operationExecution.recordMeasurements"
    EXECUTION_RECORD_QUALITY = "Production.operationExecution.recordQualityResult"
    EXECUTION_COMPLETE = "Production.operationExecution.complete"
    EXECUTION_SEND_TO_REWORK = "Production.operationExecution.sendToRework"
    EXECUTION_CANCEL = "Production.operationExecution.cancel"