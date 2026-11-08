from uuid import uuid4
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from course_aggregator.api.main import app
from course_aggregator.storage.database import get_db_session
from course_aggregator.storage.models import CourseModel, PlatformModel


@pytest.mark.asyncio
async def test_full_api_workflow(test_session: AsyncSession) -> None:
    # Підміняємо сесію бази даних на тестову
    async def override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Перевірка Health Check та заголовка Correlation ID
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers

        # 2. Створюємо тестовий курс у БД
        platform = PlatformModel(name="API Platform", url="https://api.org")
        test_session.add(platform)
        await test_session.flush()

        course = CourseModel(
            platform_id=platform.id,
            title="FastAPI Pro Course",
            url="https://api.org/fastapi",
            duration_hours=25,
            level="intermediate",
            rating=4.9,
            topics=[],
        )
        test_session.add(course)
        await test_session.commit()

        user_id = str(uuid4())
        headers = {"X-User-ID": user_id}

        # 3. Додаємо курс до плану користувача (POST /api/v1/plan)
        add_resp = await client.post(
            "/api/v1/plan",
            json={"course_id": str(course.id), "notes": "Мій перший курс"},
            headers=headers,
        )
        assert add_resp.status_code == 201
        plan_item = add_resp.json()
        item_id = plan_item["id"]
        assert plan_item["progress_percent"] == 0
        assert plan_item["status"] == "planned"

        # 4. Оновлюємо прогрес до 60% (PATCH /api/v1/plan/{id}/progress)
        patch_resp = await client.patch(
            f"/api/v1/plan/{item_id}/progress",
            json={"percent": 60},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["progress_percent"] == 60
        assert patch_resp.json()["status"] == "in_progress"

        # 5. Критерій 2: Спроба зменшити прогрес повертає 422 Unprocessable Entity
        patch_regress = await client.patch(
            f"/api/v1/plan/{item_id}/progress",
            json={"percent": 50},
            headers=headers,
        )
        assert patch_regress.status_code == 422
        assert patch_regress.headers["content-type"] == "application/problem+json"
        error_body = patch_regress.json()
        assert error_body["type"] == "https://example.com/probs/progress-regression"

        # 6. Критерій 3: Досягнення 100% переводить курс у стан «completed»
        patch_100 = await client.patch(
            f"/api/v1/plan/{item_id}/progress",
            json={"percent": 100},
            headers=headers,
        )
        assert patch_100.status_code == 200
        assert patch_100.json()["progress_percent"] == 100
        assert patch_100.json()["status"] == "completed"
        assert patch_100.json()["completed_at"] is not None

        # 7. Критерій 4: План користувача недоступний іншим користувачам
        other_user_headers = {"X-User-ID": str(uuid4())}
        other_plan_resp = await client.get("/api/v1/plan", headers=other_user_headers)
        assert other_plan_resp.status_code == 200
        assert len(other_plan_resp.json()) == 0

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_courses_search_and_filter(test_session: AsyncSession) -> None:
    """Перевірка серверної фільтрації, пошуку та пагінації курсів."""
    async def override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    platform = PlatformModel(name="Search Platform", url="https://search.org")
    test_session.add(platform)
    await test_session.flush()

    c1 = CourseModel(
        platform_id=platform.id,
        title="Advanced Python Metaprogramming",
        url="https://search.org/adv-py",
        language="ua",
        duration_hours=40,
        level="advanced",
        rating=4.9,
        topics=[],
    )
    c2 = CourseModel(
        platform_id=platform.id,
        title="Intro to JavaScript",
        url="https://search.org/intro-js",
        language="en",
        duration_hours=15,
        level="beginner",
        rating=4.2,
        topics=[],
    )
    test_session.add_all([c1, c2])
    await test_session.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Пошук за підрядком "Python"
        resp = await client.get("/api/v1/courses?q=Python")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Advanced Python Metaprogramming"

        # Фільтрація за рівнем beginner
        resp_level = await client.get("/api/v1/courses?level=beginner")
        assert resp_level.status_code == 200
        assert resp_level.json()["total"] == 1
        assert resp_level.json()["items"][0]["title"] == "Intro to JavaScript"

    app.dependency_overrides.clear()