"""
Константы событий CP-модуля (из CP_Business_Roles.yml).
Соглашение: "CP.<entity>.<action>".
"""


class CPEvents:
    # Справочники
    COUNTERPARTY_TYPE_SAVE = "CP.counterpartyType.save"
    CATEGORY_SAVE = "CP.category.save"

    # Контрагент
    COUNTERPARTY_SAVE = "CP.counterparty.save"
    COUNTERPARTY_UPDATE_STATUS = "CP.counterparty.updateStatus"
    COUNTERPARTY_ASSIGN_RESPONSIBLE = "CP.counterparty.assignResponsible"

    # Контакты
    CONTACT_PERSON_SAVE = "CP.contactPerson.save"
    CONTACT_PERSON_DELETE = "CP.contactPerson.delete"

    # Банковские счета
    BANK_ACCOUNT_SAVE = "CP.bankAccount.save"
    BANK_ACCOUNT_DELETE = "CP.bankAccount.delete"

    # Адреса
    ADDRESS_SAVE = "CP.address.save"
    ADDRESS_DELETE = "CP.address.delete"

    # Рейтинги и взаимодействия
    RATING_CREATE = "CP.rating.create"
    INTERACTION_CREATE = "CP.interaction.create"
    INTERACTION_UPDATE = "CP.interaction.update"

    # Договоры
    CONTRACT_SAVE = "CP.contract.save"
    CONTRACT_ACTIVATE = "CP.contract.activate"
    CONTRACT_TERMINATE = "CP.contract.terminate"

    # Чёрный список
    BLACKLIST_ADD = "CP.blacklist.add"
    BLACKLIST_REMOVE = "CP.blacklist.remove"

    # Документы
    ATTACHMENT_CREATE = "CP.attachment.create"
    ATTACHMENT_DELETE = "CP.attachment.delete"