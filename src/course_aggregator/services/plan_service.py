"""Сервіс керування навчальним планом користувача та ключової операції прогресу."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from course_aggregator.domain.exceptions import (
    EntityNotFoundError,
    ProgressRegressionError,
)
from course_aggregator.domain.models import PlanStatus
from course_aggregator.storage.models import CourseModel, PlanItemModel


class PlanService:
    """Сервіс навчальних планів із транзакційною гарантією інваріантів."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_course_to_plan(
        self,
        user_id: UUID,
        course_id: UUID,
        notes: str = "",
    ) -> tuple[PlanItemModel, bool]:
        """Додає курс до плану або повертає наявний (ідемпотентність).

        Повертає кортеж: (plan_item, is_created).
        """
        # Перевіряємо існування курсу
        course_stmt = select(CourseModel).where(CourseModel.id == course_id)
        course_res = await self.session.execute(course_stmt)
        course = course_res.scalars().first()
        if not course:
            raise EntityNotFoundError(f"Курс із ID {course_id} не знайдено")

        # Перевіряємо, чи вже є курс у плані користувача
        stmt = (
            select(PlanItemModel)
            .options(
                selectinload(PlanItemModel.course).selectinload(CourseModel.topics),
                selectinload(PlanItemModel.course).selectinload(CourseModel.platform),
            )
            .where(
                PlanItemModel.user_id == user_id,
                PlanItemModel.course_id == course_id,
            )
        )
        result = await self.session.execute(stmt)
        existing_item = result.scalars().first()

        if existing_item:
            return existing_item, False

        # Отримуємо наступний індекс порядку
        count_stmt = select(PlanItemModel).where(PlanItemModel.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        current_count = len(count_res.scalars().all())

        new_item = PlanItemModel(
            id=uuid4(),
            user_id=user_id,
            course_id=course_id,
            status=PlanStatus.PLANNED.value,
            order_index=current_count + 1,
            notes=notes,
            progress_percent=0,
            completed_modules=0,
            total_modules=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(new_item)
        await self.session.commit()

        # Підвантажуємо повні зв'язки з курсом, темами та платформою
        stmt_loaded = (
            select(PlanItemModel)
            .options(
                selectinload(PlanItemModel.course).selectinload(CourseModel.topics),
                selectinload(PlanItemModel.course).selectinload(CourseModel.platform),
            )
            .where(PlanItemModel.id == new_item.id)
        )
        loaded_res = await self.session.execute(stmt_loaded)
        return loaded_res.scalars().one(), True

    async def update_progress(
        self,
        user_id: UUID,
        plan_item_id: UUID,
        percent: int,
    ) -> PlanItemModel:
        """Оновлює прогрес курсу з дотриманням бізнес-правил в одній транзакції."""
        if not (0 <= percent <= 100):
            raise ProgressRegressionError("Прогрес має бути в межах від 0 до 100%")

        stmt = (
            select(PlanItemModel)
            .options(
                selectinload(PlanItemModel.course).selectinload(CourseModel.topics),
                selectinload(PlanItemModel.course).selectinload(CourseModel.platform),
            )
            .where(
                PlanItemModel.id == plan_item_id,
                PlanItemModel.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        item = result.scalars().first()

        if not item:
            raise EntityNotFoundError("Курс у плані не знайдено або немає доступу")

        # Перевірка інваріанта зростання прогресу
        if percent < item.progress_percent:
            raise ProgressRegressionError(
                f"Спроба зменшити прогрес з {item.progress_percent}% до {percent}% відхилена"
            )

        item.progress_percent = percent
        item.updated_at = datetime.now(UTC)

        if percent == 100:
            item.status = PlanStatus.COMPLETED.value
            if item.completed_at is None:
                item.completed_at = datetime.now(UTC)
        elif percent > 0:
            item.status = PlanStatus.IN_PROGRESS.value

        await self.session.commit()
        return item

    async def get_user_plan(
        self,
        user_id: UUID,
        status: str | None = None,
    ) -> list[PlanItemModel]:
        """Отримує список курсів плану конкретного користувача (ізоляція даних)."""
        query = (
            select(PlanItemModel)
            .options(
                selectinload(PlanItemModel.course).selectinload(CourseModel.topics),
                selectinload(PlanItemModel.course).selectinload(CourseModel.platform),
            )
            .where(PlanItemModel.user_id == user_id)
        )
        if status:
            query = query.where(PlanItemModel.status == status)

        query = query.order_by(PlanItemModel.order_index.asc())
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def update_notes(self, user_id: UUID, plan_item_id: UUID, notes: str) -> PlanItemModel:
        """Оновлення особистих нотаток до курсу."""
        stmt = (
            select(PlanItemModel)
            .options(
                selectinload(PlanItemModel.course).selectinload(CourseModel.topics),
                selectinload(PlanItemModel.course).selectinload(CourseModel.platform),
            )
            .where(PlanItemModel.id == plan_item_id, PlanItemModel.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        item = res.scalars().first()
        if not item:
            raise EntityNotFoundError("Курс у плані не знайдено")
        item.notes = notes
        item.updated_at = datetime.now(UTC)
        await self.session.commit()
        return item

    async def remove_from_plan(self, user_id: UUID, plan_item_id: UUID) -> None:
        """Видалення курсу з плану користувача."""
        stmt = select(PlanItemModel).where(
            PlanItemModel.id == plan_item_id, PlanItemModel.user_id == user_id
        )
        res = await self.session.execute(stmt)
        item = res.scalars().first()
        if not item:
            raise EntityNotFoundError("Курс у плані не знайдено")
        await self.session.delete(item)
        await self.session.commit()