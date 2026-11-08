"""Конвеєр нормалізації, валідації, дедуплікації та збереження зібраних курсів."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from course_aggregator.sources.base import CourseSource, IngestionStats, RawCourseData
from course_aggregator.storage.models import CourseModel, PlatformModel, TopicModel


class CourseIngestionPipeline:
    """Сервіс обробки та збереження курсів у базу даних."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_or_create_platform(self, name: str, url: str) -> PlatformModel:
        stmt = select(PlatformModel).where(PlatformModel.name == name)
        result = await self.session.execute(stmt)
        platform = result.scalars().first()
        if not platform:
            platform = PlatformModel(id=uuid4(), name=name, url=url, is_active=True)
            self.session.add(platform)
            await self.session.flush()
        return platform

    async def _get_or_create_topics(self, topic_names: list[str]) -> list[TopicModel]:
        topics: list[TopicModel] = []
        for raw_name in topic_names:
            normalized_name = raw_name.strip()
            if not normalized_name:
                continue

            stmt = select(TopicModel).where(TopicModel.name == normalized_name)
            result = await self.session.execute(stmt)
            topic = result.scalars().first()
            if not topic:
                topic = TopicModel(id=uuid4(), name=normalized_name)
                self.session.add(topic)
                await self.session.flush()
            topics.append(topic)
        return topics

    def _validate_raw_data(self, item: RawCourseData) -> bool:
        """Перевірка валідності вхідних даних (відсікає некоректні записи)."""
        if not item.title or not item.title.strip():
            return False
        if item.duration_hours < 0:
            return False
        if not (0.0 <= item.rating <= 5.0):
            return False
        return True

    async def process_source(self, source: CourseSource) -> IngestionStats:
        """Запускає повний цикл обробки потоку даних від джерела."""
        stats = IngestionStats()
        platform = await self._get_or_create_platform(source.platform_name, source.platform_url)

        # Отримуємо наявні назви курсів цієї платформи для дедуплікації
        stmt = select(CourseModel.title).where(CourseModel.platform_id == platform.id)
        existing_titles = set((await self.session.execute(stmt)).scalars().all())

        async for raw_item in source.fetch_courses():
            stats.total_received += 1

            # Валідація
            if not self._validate_raw_data(raw_item):
                stats.rejected_count += 1
                continue

            clean_title = raw_item.title.strip()

            # Дедуплікація в межах однієї платформи
            if clean_title in existing_titles:
                stats.duplicates_skipped += 1
                continue

            topics = await self._get_or_create_topics(raw_item.topics)

            new_course = CourseModel(
                id=uuid4(),
                platform_id=platform.id,
                title=clean_title,
                url=raw_item.url,
                language=raw_item.language,
                duration_hours=raw_item.duration_hours,
                level=raw_item.level,
                rating=raw_item.rating,
                topics=topics,
            )
            self.session.add(new_course)
            existing_titles.add(clean_title)
            stats.valid_courses += 1

        await self.session.commit()
        return stats