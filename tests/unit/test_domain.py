from uuid import uuid4
import pytest

from course_aggregator.domain.exceptions import ProgressRegressionError
from course_aggregator.domain.models import PlanItem, PlanStatus


def test_progress_regression_raises_error() -> None:
    """Перевірка заборони зменшення прогресу."""
    user_id = uuid4()
    course_id = uuid4()
    item = PlanItem(user_id=user_id, course_id=course_id)

    # Збільшуємо до 40%
    item.update_progress(40)
    assert item.progress.percent == 40
    assert item.status == PlanStatus.IN_PROGRESS

    # Спроба зменшити до 30% має викликати помилку
    with pytest.raises(ProgressRegressionError):
        item.update_progress(30)


def test_progress_completion_sets_status_and_date() -> None:
    """Перевірка автоматичного завершення курсу при 100%."""
    user_id = uuid4()
    course_id = uuid4()
    item = PlanItem(user_id=user_id, course_id=course_id)

    item.update_progress(100)
    assert item.progress.percent == 100
    assert item.status == PlanStatus.COMPLETED
    assert item.completed_at is not None