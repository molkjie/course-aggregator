from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from course_aggregator.services.analytics_service import AnalyticsService
from course_aggregator.services.plan_service import PlanService
from course_aggregator.storage.models import CourseModel, PlatformModel, TopicModel


@pytest.mark.asyncio
async def test_analytics_coverage_and_ratings(test_session: AsyncSession) -> None:
    platform = PlatformModel(name="AnalyticsPlatform", url="https://plat.org")
    test_session.add(platform)
    await test_session.flush()

    topic = TopicModel(name="FastAPI")
    test_session.add(topic)
    await test_session.flush()

    course = CourseModel(
        platform_id=platform.id,
        title="Async Python & FastAPI",
        url="https://plat.org/fastapi",
        level="beginner",
        rating=4.5,
        topics=[topic],
    )
    test_session.add(course)
    await test_session.commit()

    user_id = uuid4()
    plan_service = PlanService(test_session)
    item, _ = await plan_service.add_course_to_plan(user_id, course.id)
    await plan_service.update_progress(user_id, item.id, 100)

    analytics = AnalyticsService(test_session)

    coverage = await analytics.get_topics_coverage(user_id)
    assert coverage.get("FastAPI") == 1

    ratings = await analytics.get_average_rating_by_topics()
    assert ratings.get("FastAPI") == 4.5

    dynamics = await analytics.get_monthly_completion_dynamics(user_id)
    assert len(dynamics) >= 1
