"""Сервіс побудови аналітичних звітів."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from course_aggregator.domain.models import PlanStatus
from course_aggregator.storage.models import (
    CourseModel,
    PlanItemModel,
    TopicModel,
    course_topics,
)


class AnalyticsService:
    """Сервіс агрегації статистики та аналітики."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_topics_coverage(self, user_id: UUID) -> dict[str, int]:
        """Аналітика 1: Покриття тем у плані користувача (скільки курсів з кожної теми)."""
        stmt = (
            select(PlanItemModel)
            .options(selectinload(PlanItemModel.course).selectinload(CourseModel.topics))
            .where(PlanItemModel.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        plan_items = result.scalars().all()

        coverage: dict[str, int] = defaultdict(int)
        for item in plan_items:
            for topic in item.course.topics:
                coverage[topic.name] += 1

        return dict(coverage)

    async def get_average_rating_by_topics(self) -> dict[str, float]:
        """Аналітика 2: Середній рейтинг курсів за темами."""
        stmt = (
            select(
                TopicModel.name,
                func.avg(CourseModel.rating).label("avg_rating"),
            )
            .join(course_topics, TopicModel.id == course_topics.c.topic_id)
            .join(CourseModel, CourseModel.id == course_topics.c.course_id)
            .group_by(TopicModel.name)
        )
        result = await self.session.execute(stmt)
        return {name: round(float(avg_r), 2) for name, avg_r in result.all()}

    async def get_monthly_completion_dynamics(self, user_id: UUID) -> dict[str, int]:
        """Аналітика 3: Динаміка завершення курсів по місяцях (РРРР-ММ)."""
        stmt = select(PlanItemModel).where(
            PlanItemModel.user_id == user_id,
            PlanItemModel.status == PlanStatus.COMPLETED.value,
            PlanItemModel.completed_at.is_not(None),
        )
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        dynamics: dict[str, int] = defaultdict(int)
        for item in items:
            if item.completed_at:
                month_key = item.completed_at.strftime("%Y-%m")
                dynamics[month_key] += 1

        return dict(dynamics)
