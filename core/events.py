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


class ProcurementEvents:
    """События Procurement-модуля (из PROCUREMENT_Business_Roles.yml)."""
    # Поставщики
    SUPPLIER_SAVE = "Procurement.supplier.save"

    # Заявки
    REQUISITION_CREATE = "Procurement.requisition.create"
    REQUISITION_LINE_CREATE = "Procurement.requisitionLine.create"
    REQUISITION_LINE_UPDATE = "Procurement.requisitionLine.update"
    REQUISITION_REVIEW = "Procurement.requisition.review"

    # RFQ
    RFQ_CREATE = "Procurement.rfq.create"
    RFQ_SUPPLIER_ADD = "Procurement.rfqSupplier.add"
    SUPPLIER_QUOTE_CREATE = "Procurement.supplierQuote.create"
    RFQ_CLOSE = "Procurement.rfq.close"

    # Заказы
    ORDER_CREATE = "Procurement.order.create"
    ORDER_LINE_CREATE = "Procurement.orderLine.create"
    ORDER_LINE_UPDATE = "Procurement.orderLine.update"
    ORDER_CONFIRM = "Procurement.order.confirm"
    ORDER_RECEIVE = "Procurement.order.receive"
    ORDER_RECEIVE_COMPLETE = "Procurement.order.receive_complete"
    ORDER_CANCEL = "Procurement.order.cancel"