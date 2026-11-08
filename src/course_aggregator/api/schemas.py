"""Схеми Pydantic для валідації вхідних даних та серіалізації відповідей API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from course_aggregator.domain.models import CourseLevel, PlanStatus


class TopicResponse(BaseModel):
    """Схема відображення теми."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class PlatformResponse(BaseModel):
    """Схема відображення платформи."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str


class CourseResponse(BaseModel):
    """Схема відображення курсу."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str
    language: str
    duration_hours: int
    level: str
    rating: float
    platform: PlatformResponse | None = None
    topics: list[TopicResponse] = Field(default_factory=list)


class CoursePageResponse(BaseModel):
    """Посторінкова відповідь для курсів."""

    items: list[CourseResponse]
    total: int
    page: int
    page_size: int


class AddToPlanRequest(BaseModel):
    """Тіло запиту на додавання курсу до плану."""

    course_id: UUID
    notes: str = ""


class UpdateProgressRequest(BaseModel):
    """Тіло запиту на оновлення прогресу."""

    percent: int = Field(ge=0, le=100, description="Відсоток виконання курсу (0-100)")


class PlanItemResponse(BaseModel):
    """Схема відображення елемента плану навчання."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    course_id: UUID
    status: str
    order_index: int
    notes: str
    progress_percent: int
    completed_modules: int
    total_modules: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    course: CourseResponse | None = None


class ProblemDetail(BaseModel):
    """Стандартний формат деталей помилки за стандартом RFC 9457."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None

class UpdateNotesRequest(BaseModel):
    """Тіло запиту на зміну нотаток до курсу."""

    notes: str = Field(description="Нотатки користувача до курсу")