"""Інтерфейс командного рядка (CLI) для адміністрування системи."""

import asyncio
import typer
from rich.console import Console
from rich.table import Table

from course_aggregator.sources.base import CourseSource
from course_aggregator.sources.clients import CourseraSource, StepikSource
from course_aggregator.sources.pipeline import CourseIngestionPipeline
from course_aggregator.storage.database import async_session_factory
from course_aggregator.storage.seeder import seed_database

cli_app = typer.Typer(help="CLI утиліта агрегатора онлайн-курсів")
console = Console()


@cli_app.command("seed")
def seed() -> None:
    """Наповнити базу тестовими seed-даними (200+ курсів)."""
    console.print("[yellow]Початок генерації seed-даних...[/yellow]")
    asyncio.run(seed_database())
    console.print("[green]Успішно завершено![/green]")


@cli_app.command("ingest")
def ingest() -> None:
    """Запустити збір курсів із зовнішніх платформ (Coursera, Stepik)."""
    async def run() -> None:
        async with async_session_factory() as session:
            pipeline = CourseIngestionPipeline(session)
            sources: list[CourseSource] = [CourseraSource(), StepikSource()]
            for src in sources:
                console.print(f"[cyan]Збір даних із платформи: {src.platform_name}...[/cyan]")
                stats = await pipeline.process_source(src)
                table = Table(title=f"Статистика: {src.platform_name}")
                table.add_column("Показник", style="cyan")
                table.add_column("Значення", style="magenta")
                table.add_row("Отримано записів", str(stats.total_received))
                table.add_row("Збережено валідних", str(stats.valid_courses))
                table.add_row("Відхилено битих", str(stats.rejected_count))
                table.add_row("Пропущено дублікатів", str(stats.duplicates_skipped))
                console.print(table)

    asyncio.run(run())


if __name__ == "__main__":
    cli_app()