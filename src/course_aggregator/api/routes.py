"""Маршрути REST API для роботи з курсами, планами та аналітикою."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from course_aggregator.api.schemas import (
    AddToPlanRequest,
    CoursePageResponse,
    CourseResponse,
    PlanItemResponse,
    UpdateNotesRequest,
    UpdateProgressRequest,
)
from course_aggregator.services.analytics_service import AnalyticsService
from course_aggregator.services.plan_service import PlanService
from course_aggregator.storage.database import get_db_session
from course_aggregator.storage.models import CourseModel, PlatformModel, TopicModel

router = APIRouter(prefix="/api/v1")


def get_current_user_id(x_user_id: Annotated[UUID | None, Header()] = None) -> UUID:
    """Отримує ідентифікатор користувача із заголовка або генерує дефолтний."""
    if x_user_id:
        return x_user_id
    # За замовчуванням фіксований тестовий ID для сесії
    return UUID("11111111-1111-1111-1111-111111111111")


@router.get("/courses", response_model=CoursePageResponse, summary="Пошук та фільтрація курсів")
async def list_courses(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    q: Annotated[str | None, Query(description="Пошуковий запит по назві")] = None,
    topic: Annotated[str | None, Query(description="Фільтр за назвою теми")] = None,
    level: Annotated[str | None, Query(description="Рівень складності")] = None,
    platform: Annotated[str | None, Query(description="Назва платформи")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CoursePageResponse:
    query = select(CourseModel).options(
        selectinload(CourseModel.platform),
        selectinload(CourseModel.topics),
    )

    if q:
        query = query.where(CourseModel.title.ilike(f"%{q}%"))
    if level:
        query = query.where(CourseModel.level == level)
    if platform:
        query = query.join(CourseModel.platform).where(PlatformModel.name.ilike(f"%{platform}%"))
    if topic:
        query = query.join(CourseModel.topics).where(TopicModel.name.ilike(f"%{topic}%"))

    # Загальна кількість записів під фільтр
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Серверна пагінація (OFFSET / LIMIT)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    items = result.scalars().all()

    return CoursePageResponse(
        items=[CourseResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/plan",
    response_model=PlanItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додавання курсу до плану",
)
async def add_to_plan(
    body: AddToPlanRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> PlanItemResponse:
    service = PlanService(session)
    plan_item, _ = await service.add_course_to_plan(
        user_id=user_id,
        course_id=body.course_id,
        notes=body.notes,
    )
    return PlanItemResponse.model_validate(plan_item)


@router.patch(
    "/plan/{item_id}/progress", response_model=PlanItemResponse, summary="Оновлення прогресу"
)
async def update_progress(
    item_id: UUID,
    body: UpdateProgressRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> PlanItemResponse:
    service = PlanService(session)
    updated_item = await service.update_progress(
        user_id=user_id,
        plan_item_id=item_id,
        percent=body.percent,
    )
    return PlanItemResponse.model_validate(updated_item)


@router.get("/plan", response_model=list[PlanItemResponse], summary="Отримання плану користувача")
async def get_my_plan(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    plan_status: Annotated[str | None, Query(alias="status")] = None,
) -> list[PlanItemResponse]:
    service = PlanService(session)
    items = await service.get_user_plan(user_id=user_id, status=plan_status)
    return [PlanItemResponse.model_validate(item) for item in items]


@router.get("/stats/topics-coverage", summary="Аналітика покриття тем у плані")
async def get_topics_coverage(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, int]:
    analytics = AnalyticsService(session)
    return await analytics.get_topics_coverage(user_id)


@router.patch(
    "/plan/{item_id}/notes", response_model=PlanItemResponse, summary="Оновлення нотаток до курсу"
)
async def update_notes(
    item_id: UUID,
    body: UpdateNotesRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> PlanItemResponse:
    service = PlanService(session)
    updated = await service.update_notes(user_id=user_id, plan_item_id=item_id, notes=body.notes)
    return PlanItemResponse.model_validate(updated)


@router.delete(
    "/plan/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Видалення курсу з плану"
)
async def remove_plan_item(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> None:
    service = PlanService(session)
    await service.remove_from_plan(user_id=user_id, plan_item_id=item_id)


@router.get("/stats/ratings-by-topic", summary="Середній рейтинг курсів за темами")
async def get_ratings_by_topic(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, float]:
    analytics = AnalyticsService(session)
    return await analytics.get_average_rating_by_topics()


@router.get("/stats/completion-dynamics", summary="Динаміка завершення курсів по місяцях")
async def get_completion_dynamics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, int]:
    analytics = AnalyticsService(session)
    return await analytics.get_monthly_completion_dynamics(user_id)
