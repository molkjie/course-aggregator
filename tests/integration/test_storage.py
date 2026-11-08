import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from course_aggregator.storage.models import PlatformModel


@pytest.mark.asyncio
async def test_seed_and_query_database(test_session: AsyncSession) -> None:
    """Перевірка створення платформ у сесії."""
    coursera = PlatformModel(name="Coursera Test", url="https://coursera.org", is_active=True)
    stepik = PlatformModel(name="Stepik Test", url="https://stepik.org", is_active=True)
    test_session.add_all([coursera, stepik])
    await test_session.commit()

    result = await test_session.execute(select(PlatformModel))
    platforms = result.scalars().all()
    assert len(platforms) >= 2
