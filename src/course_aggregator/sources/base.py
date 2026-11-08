"""Базовий протокол та структури для збору даних із зовнішніх платформ."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawCourseData:
    """Сирі ненормалізовані дані курсу, отримані з API/каталогу."""

    external_id: str
    title: str
    url: str
    topics: list[str]
    language: str = "ua"
    duration_hours: int = 0
    level: str = "beginner"
    rating: float = 0.0


@dataclass(slots=True)
class IngestionStats:
    """Статистика результату збору даних для звітності."""

    total_received: int = 0
    valid_courses: int = 0
    rejected_count: int = 0
    duplicates_skipped: int = 0


class CourseSource(Protocol):
    """Протокол, який має реалізовувати кожен клієнт зовнішнього джерела."""

    platform_name: str
    platform_url: str

    def fetch_courses(self) -> AsyncIterator[RawCourseData]:
        """Асинхронний генератор для ледачого отримання сирих даних курсів."""
        ...
