"""SQLAlchemy 2.0 моделі таблиць бази даних."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from course_aggregator.domain.models import CourseLevel, PlanStatus
from course_aggregator.storage.database import Base


class GUID(TypeDecorator[UUID]):
    """Кросплатформний тип UUID (сумісний із SQLite та PostgreSQL)."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: object, dialect: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: object, dialect: object) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        return UUID(str(value))

# Таблиця зв'язку багато-до-багатьох: Course <-> Topic
course_topics = Table(
    "course_topics",
    Base.metadata,
    Column("course_id", GUID(), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", GUID(), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)


class PlatformModel(Base):
    """Таблиця освітніх платформ."""

    __tablename__ = "platforms"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    courses: Mapped[list["CourseModel"]] = relationship(
        back_populates="platform", cascade="all, delete-orphan"
    )


class TopicModel(Base):
    """Таблиця тем курсів."""

    __tablename__ = "topics"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    courses: Mapped[list["CourseModel"]] = relationship(
        secondary=course_topics, back_populates="topics"
    )


class CourseModel(Base):
    """Таблиця курсів із індексами для швидкої фільтрації."""

    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    platform_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="ua", nullable=False, index=True)
    duration_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[str] = mapped_column(
        String(20), default=CourseLevel.BEGINNER.value, nullable=False, index=True
    )
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Зв'язки
    platform: Mapped["PlatformModel"] = relationship(back_populates="courses")
    topics: Mapped[list["TopicModel"]] = relationship(
        secondary=course_topics, back_populates="courses"
    )
    plan_items: Mapped[list["PlanItemModel"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Дедуплікація курсів: на одній платформі не може бути двох однакових назв курсів
        UniqueConstraint("platform_id", "title", name="uq_platform_course_title"),
        Index("ix_courses_search", "title", "language", "level"),
    )


class PlanItemModel(Base):
    """Таблиця курсів у плані користувача."""

    __tablename__ = "plan_items"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False, index=True)
    course_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PlanStatus.PLANNED.value, nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Прогрес зберігається прямо в записі плану
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_modules: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_modules: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped["CourseModel"] = relationship(back_populates="plan_items")

    __table_args__ = (
        # Вимога ТЗ: курс додається до плану користувача лише один раз
        UniqueConstraint("user_id", "course_id", name="uq_user_course_plan"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="chk_progress_range"),
    )