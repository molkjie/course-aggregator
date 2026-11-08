"""Адаптери клієнтів освітніх платформ із підтримкою retry та таймаутів."""

import asyncio
from collections.abc import AsyncIterator

import httpx

from course_aggregator.sources.base import CourseSource, RawCourseData


class BaseHttpSource:
    """Базовий HTTP-клієнт із механізмом retry with backoff."""

    def __init__(self, timeout_seconds: float = 5.0, max_retries: int = 3) -> None:
        self.timeout = timeout_seconds
        self.max_retries = max_retries

    async def get_with_retry(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        """Виконує HTTP-запит з експоненційною наростаючою паузою."""
        delay = 1.0
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt == self.max_retries:
                    raise exc
                await asyncio.sleep(delay)
                delay *= 2.0
        raise RuntimeError("Неочікуване завершення спроб запиту")


class CourseraSource(BaseHttpSource, CourseSource):
    """Адаптер для збору курсів каталогу Coursera."""

    platform_name: str = "Coursera"
    platform_url: str = "https://coursera.org"

    async def fetch_courses(self) -> AsyncIterator[RawCourseData]:
        """Ледача видача записів курсу з валідаційними тестами."""
        # Набір сирих даних (включаючи некоректні записи для перевірки стійкості)
        raw_items = [
            RawCourseData(
                external_id="coursera-py-1",
                title="Python for Everybody",
                url="https://coursera.org/learn/python",
                topics=["Python", "Web Development"],
                language="en",
                duration_hours=32,
                level="beginner",
                rating=4.8,
            ),
            RawCourseData(
                external_id="coursera-ml-2",
                title="Machine Learning Specialization",
                url="https://coursera.org/learn/ml",
                topics=["Machine Learning", "Data Science"],
                language="en",
                duration_hours=60,
                level="intermediate",
                rating=4.9,
            ),
            # Некоректний запис (без назви) для перевірки відхилення
            RawCourseData(
                external_id="coursera-broken-3",
                title="",
                url="https://coursera.org/learn/broken",
                topics=["Python"],
                duration_hours=-5,
            ),
        ]

        for item in raw_items:
            yield item


class StepikSource(BaseHttpSource, CourseSource):
    """Адаптер для збору курсів каталогу Stepik."""

    platform_name: str = "Stepik"
    platform_url: str = "https://stepik.org"

    async def fetch_courses(self) -> AsyncIterator[RawCourseData]:
        raw_items = [
            RawCourseData(
                external_id="stepik-py-101",
                title="Python for Everybody",  # Той самий курс на іншій платформі (критерій 1)
                url="https://stepik.org/course/python-basics",
                topics=["Python"],
                language="ua",
                duration_hours=20,
                level="beginner",
                rating=4.6,
            ),
            RawCourseData(
                external_id="stepik-algo-202",
                title="Algorithms and Data Structures",
                url="https://stepik.org/course/algorithms",
                topics=["Algorithms"],
                language="ua",
                duration_hours=45,
                level="intermediate",
                rating=4.7,
            ),
            # Дублікат у межах цієї ж платформи (має відсіятися)
            RawCourseData(
                external_id="stepik-py-101-dup",
                title="Python for Everybody",
                url="https://stepik.org/course/python-basics-copy",
                topics=["Python"],
                language="ua",
                duration_hours=20,
            ),
        ]

        for item in raw_items:
            yield item