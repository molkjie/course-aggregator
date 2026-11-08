"""Скрипт вимірювання продуктивності для Розділу 4 пояснювальної записки."""

import asyncio
import sys
import time
from uuid import uuid4

from sqlalchemy import text

from course_aggregator.services.plan_service import PlanService
from course_aggregator.storage.database import async_session_factory, engine
from course_aggregator.storage.models import CourseModel, PlatformModel


def test_memory_lazy_vs_eager() -> None:
    """Вимірювання споживання пам'яті: ледачий генератор vs жадібний список."""
    # Жадібний підхід: генерація 100 000 елементів у список
    eager_data = [{"id": i, "title": f"Course {i}"} for i in range(100_000)]
    eager_size = sys.getsizeof(eager_data)

    # Ледачий підхід: генератор
    lazy_gen = ({"id": i, "title": f"Course {i}"} for i in range(100_000))
    lazy_size = sys.getsizeof(lazy_gen)

    print(f"[MEMORY] Жадібний список (100k записів): {eager_size / 1024:.2f} KB")
    print(f"[MEMORY] Ледачий генератор (100k записів): {lazy_size / 1024:.2f} KB")
    print(f"[MEMORY] Економія пам'яті: {(eager_size / lazy_size):.1f}x разів")


async def benchmark_plan_operation() -> None:
    """Вимірювання середнього часу ключової операції оновлення прогресу."""
    user_id = uuid4()
    async with async_session_factory() as session:
        # Створюємо тестові дані
        platform = PlatformModel(name=f"BenchPlat_{uuid4()}", url="https://bench.org")
        session.add(platform)
        await session.flush()

        course = CourseModel(
            platform_id=platform.id,
            title="Benchmark Course",
            url="https://bench.org/c",
            level="beginner",
            duration_hours=10,
            rating=5.0,
            topics=[],
        )
        session.add(course)
        await session.commit()

        service = PlanService(session)
        item, _ = await service.add_course_to_plan(user_id, course.id)

        # Замір часу 100 операцій оновлення прогресу
        iterations = 50
        start_time = time.perf_counter()
        for pct in range(1, iterations + 1):
            await service.update_progress(user_id, item.id, pct)
        elapsed = time.perf_counter() - start_time

        avg_op_time = (elapsed / iterations) * 1000
        print(f"[LATENCY] Середній час операції оновлення прогресу: {avg_op_time:.2f} мс")


async def benchmark_query_plan() -> None:
    """Отримання плану виконання пошукового запиту (EXPLAIN QUERY PLAN)."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "EXPLAIN QUERY PLAN SELECT * FROM courses WHERE title LIKE '%Python%' AND level = 'beginner'"
            )
        )
        print("\n[EXPLAIN QUERY PLAN]:")
        for row in result.all():
            print(f" -> {row}")


async def main() -> None:
    print("=== ПОЧАТОК ТЕСТУВАННЯ ПРОДУКТИВНОСТІ ===")
    test_memory_lazy_vs_eager()
    await benchmark_plan_operation()
    await benchmark_query_plan()
    print("=== ТЕСТУВАННЯ ЗАВЕРШЕНО ===")


if __name__ == "__main__":
    asyncio.run(main())
