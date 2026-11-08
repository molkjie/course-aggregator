# Course Aggregator API (Агрегатор онлайн-курсів за темами)

Серверний веб-застосунок на мові Python для агрегації, каталогізації онлайн-курсів із зовнішніх платформ, планування навчання, відстеження прогресу та формування аналітичних звітів.

## 🛠 Технологічний стек
- **Мова:** Python 3.12+
- **Веб-фреймворк:** FastAPI (ASGI, Uvicorn)
- **СУБД та ORM:** PostgreSQL / SQLite (asyncpg, aiosqlite), SQLAlchemy 2.0 (async), Alembic
- **Валідація та серіалізація:** Pydantic V2 (RFC 9457 Problem Details)
- **Збір даних:** HTTPX (асинхронний клієнт із retry with exponential backoff)
- **Якість коду:** mypy (strict), ruff, pytest, pytest-cov (> 75%)
- **Журналювання:** Structlog (структуровані JSON-логи з Correlation ID)
- **Контейнеризація:** Docker, Docker Compose
- **CI/CD:** GitHub Actions

## 🏛 Архітектура застосунку
Застосунок побудовано за принципами чистої шарової архітектури (Layered Architecture):
- `domain/` — доменні моделі та чисті бізнес-інваріанти (не залежить від зовнішніх бібліотек).
- `services/` — сценарії використання, бізнес-транзакції та аналітика.
- `sources/` — адаптери збору даних із зовнішніх освітніх платформ (Coursera, Stepik).
- `storage/` — шар персистентності: моделі SQLAlchemy, міграції Alembic, генерація seed-даних.
- `api/` — транспортний шар: маршрути FastAPI, схеми DTO, middleware, обробка винятків за RFC 9457.
- `cli.py` — консольний інтерфейс адміністратора на базі Typer.

## 🚀 Швидкий запуск

### 1. Локальний запуск у віртуальному середовищі
```powershell
# Створення та активація середовища
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Встановлення залежностей
pip install -e ".[dev]"

# Застосування міграцій
alembic upgrade head

# Наповнення бази початковими seed-даними (220 курсів)
python -m course_aggregator.cli seed

# Запуск сервера
uvicorn course_aggregator.api.main:app --reload