"""Чисті доменні моделі з типізацією та інваріантами предметної області."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from course_aggregator.domain.exceptions import (
    InvalidEntityStateError,
    ProgressRegressionError,
)


class UserRole(StrEnum):
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"


class CourseLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PlanStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class Topic:
    """Тема/категорія курсу."""

    name: str
    id: UUID = field(default_factory=uuid4)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidEntityStateError("Назва теми не може бути порожньою")


@dataclass(frozen=True, slots=True)
class Platform:
    """Платформа онлайн-освіти (джерело даних)."""

    name: str
    url: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidEntityStateError("Назва платформи не може бути порожньою")


@dataclass(slots=True)
class Course:
    """Сутність курсу."""

    platform_id: UUID
    title: str
    url: str
    id: UUID = field(default_factory=uuid4)
    language: str = "ua"
    duration_hours: int = 0
    level: CourseLevel = CourseLevel.BEGINNER
    rating: float = 0.0
    topics: list[Topic] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise InvalidEntityStateError("Назва курсу не може бути порожньою")
        if self.duration_hours < 0:
            raise InvalidEntityStateError("Тривалість курсу не може бути від'ємною")
        if not (0.0 <= self.rating <= 5.0):
            raise InvalidEntityStateError("Рейтинг має бути в діапазоні від 0.0 до 5.0")


@dataclass(slots=True)
class Progress:
    """Об'єкт фіксації прогресу навчання з інваріантами."""

    percent: int = 0
    completed_modules: int = 0
    total_modules: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def update_percent(self, new_percent: int) -> None:
        """Оновлює прогрес тільки в бік збільшення."""
        if not (0 <= new_percent <= 100):
            raise ProgressRegressionError("Прогрес повинен бути в межах від 0 до 100%")
        if new_percent < self.percent:
            raise ProgressRegressionError(
                f"Неможливо зменшити прогрес з {self.percent}% до {new_percent}%"
            )
        self.percent = new_percent
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class PlanItem:
    """Курс у навчальному плані користувача."""

    user_id: UUID
    course_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: PlanStatus = PlanStatus.PLANNED
    order_index: int = 0
    notes: str = ""
    progress: Progress = field(default_factory=Progress)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def update_progress(self, percent: int) -> None:
        """Оновлює прогрес та переводить стан у completed при 100%."""
        self.progress.update_percent(percent)

        if percent == 100:
            self.status = PlanStatus.COMPLETED
            if self.completed_at is None:
                self.completed_at = datetime.now(UTC)
        elif percent > 0:
            self.status = PlanStatus.IN_PROGRESS
