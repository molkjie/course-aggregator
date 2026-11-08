from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from course_aggregator.domain.exceptions import ProgressRegressionError
from course_aggregator.domain.models import CourseLevel, PlanStatus
from course_aggregator.services.plan_service import PlanService
from course_aggregator.storage.models import CourseModel, PlatformModel


@pytest.mark.asyncio
async def test_plan_service_flow(test_session: AsyncSession) -> None:
    # 1. Підготовка платформи та курсу
    platform = PlatformModel(name="TestPlatform", url="https://test.org")
    test_session.add(platform)
    await test_session.flush()

    course = CourseModel(
        platform_id=platform.id,
        title="Python Deep Dive",
        url="https://test.org/py",
        level=CourseLevel.BEGINNER.value,
        duration_hours=10,
        rating=4.8,
    )
    test_session.add(course)
    await test_session.commit()

    service = PlanService(test_session)
    user_a = uuid4()
    user_b = uuid4()

    # 2. Додавання курсу до плану (Критерій 1: курс додається один раз)
    item_1, created_1 = await service.add_course_to_plan(user_a, course.id)
    assert created_1 is True
    assert item_1.status == PlanStatus.PLANNED.value

    # Повторне додавання повертає наявний запис (ідемпотентність)
    item_2, created_2 = await service.add_course_to_plan(user_a, course.id)
    assert created_2 is False
    assert item_1.id == item_2.id

    # 3. Оновлення прогресу до 50%
    updated = await service.update_progress(user_a, item_1.id, 50)
    assert updated.progress_percent == 50
    assert updated.status == PlanStatus.IN_PROGRESS.value

    # 4. Спроба зменшити прогрес (Критерій 2: заборона регресу)
    with pytest.raises(ProgressRegressionError):
        await service.update_progress(user_a, item_1.id, 40)

    # 5. Досягнення 100% (Критерій 3: завершення та фіксація дати)
    completed = await service.update_progress(user_a, item_1.id, 100)
    assert completed.progress_percent == 100
    assert completed.status == PlanStatus.COMPLETED.value
    assert completed.completed_at is not None

    # 6. Критерій 4: План користувача А недоступний користувачу Б
    plan_user_b = await service.get_user_plan(user_b)
    assert len(plan_user_b) == 0

    plan_user_a = await service.get_user_plan(user_a)
    assert len(plan_user_a) == 1
