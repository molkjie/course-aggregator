"""Доменні винятки предметної області."""


class DomainError(Exception):
    """Базовий клас для всіх доменних помилок."""


class ProgressRegressionError(DomainError):
    """Виникає при спробі зменшити прогрес або встановити некоректне значення."""


class CourseAlreadyInPlanError(DomainError):
    """Виникає при спробі повторно додати курс до плану."""


class EntityNotFoundError(DomainError):
    """Виникає, коли сутність не знайдена в системі."""


class InvalidEntityStateError(DomainError):
    """Виникає при спробі виконати невалідне переведення стану."""
