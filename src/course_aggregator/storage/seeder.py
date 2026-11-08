"""Модуль наповнення бази даних початковими seed-даними (200+ курсів)."""

import asyncio
import random
from uuid import uuid4

from sqlalchemy import select

from course_aggregator.domain.models import CourseLevel
from course_aggregator.storage.database import Base, async_session_factory, engine
from course_aggregator.storage.models import CourseModel, PlatformModel, TopicModel


async def seed_database() -> None:
    """Створює схему таблиць і наповнює її понад 200 курсами."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Перевіряємо, чи база вже не наповнена
        res = await session.execute(select(PlatformModel))
        if res.scalars().first():
            print("База даних вже містить початкові дані.")
            return

        # 1. Створюємо освітні платформи
        coursera = PlatformModel(
            id=uuid4(), name="Coursera", url="https://coursera.org", is_active=True
        )
        stepik = PlatformModel(id=uuid4(), name="Stepik", url="https://stepik.org", is_active=True)
        session.add_all([coursera, stepik])
        platforms = [coursera, stepik]

        # 2. Створюємо теми (Topics)
        topic_names = [
            "Python",
            "Web Development",
            "Data Science",
            "Machine Learning",
            "DevOps",
            "Cybersecurity",
            "Databases",
            "Algorithms",
            "Mobile Development",
            "Cloud Computing",
        ]
        topic_models = [TopicModel(id=uuid4(), name=name) for name in topic_names]
        session.add_all(topic_models)

        # 3. Генеруємо 220 різноманітних курсів
        languages = ["ua", "en"]
        levels = [
            CourseLevel.BEGINNER.value,
            CourseLevel.INTERMEDIATE.value,
            CourseLevel.ADVANCED.value,
        ]

        courses_count = 220
        courses: list[CourseModel] = []

        for i in range(1, courses_count + 1):
            platform = random.choice(platforms)
            selected_topics = random.sample(topic_models, k=random.randint(1, 3))
            primary_topic = selected_topics[0].name

            course = CourseModel(
                id=uuid4(),
                platform_id=platform.id,
                title=f"{primary_topic} Masterclass: Part {i}",
                url=f"{platform.url}/learn/{primary_topic.lower()}-{i}",
                language=random.choice(languages),
                duration_hours=random.randint(5, 80),
                level=random.choice(levels),
                rating=round(random.uniform(3.5, 5.0), 1),
                topics=selected_topics,
            )
            courses.append(course)

        session.add_all(courses)
        await session.commit()
        print(f"Успішно створено {courses_count} курсів та заповнено базу даних.")


if __name__ == "__main__":
    asyncio.run(seed_database())
