"""Керування асинхронною сесією та підключенням до бази даних."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./courses.db")

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовий клас для всіх ORM-моделей."""


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор сесій бази даних для ін'єкції залежностей."""
    async with async_session_factory() as session:
        yield session