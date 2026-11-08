import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from course_aggregator.sources.clients import CourseraSource, StepikSource
from course_aggregator.sources.pipeline import CourseIngestionPipeline
from course_aggregator.storage.models import CourseModel


@pytest.mark.asyncio
async def test_sources_pipeline_ingestion_and_deduplication(test_session: AsyncSession) -> None:
    """Перевірка дедуплікації, відсікання битих записів та імпорту з 2 платформ."""
    pipeline = CourseIngestionPipeline(test_session)

    # 1. Запускаємо Coursera
    coursera_stats = await pipeline.process_source(CourseraSource())
    assert coursera_stats.total_received == 3
    assert coursera_stats.valid_courses == 2
    assert coursera_stats.rejected_count == 1  # Битий запис успішно відхилено

    # 2. Запускаємо Stepik
    stepik_stats = await pipeline.process_source(StepikSource())
    assert stepik_stats.total_received == 3
    assert stepik_stats.valid_courses == 2
    assert stepik_stats.duplicates_skipped == 1  # Дублікат у межах Stepik пропущено

    # 3. Перевіряємо Критерій приймання 1:
    # Той самий курс із двох платформ зберігається як 2 записи
    stmt = (
        select(CourseModel)
        .options(selectinload(CourseModel.platform))
        .where(CourseModel.title == "Python for Everybody")
    )
    res = await test_session.execute(stmt)
    courses = res.scalars().all()
    assert len(courses) == 2
    assert {c.platform.name for c in courses} == {"Coursera", "Stepik"}
