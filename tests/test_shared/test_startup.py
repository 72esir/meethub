"""
Тесты для shared/startup.py: wait_for_database.
"""
from unittest.mock import MagicMock, patch, call

import pytest
from sqlalchemy.exc import OperationalError

from shared.startup import wait_for_database


def _make_engine(*, fail_times=0):
    """Создаёт mock-engine, который провалится `fail_times` раз, затем успешно выполнит SELECT 1."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    if fail_times == 0:
        conn.execute.return_value = MagicMock()
    else:
        side_effects = [OperationalError("conn refused", None, None)] * fail_times + [MagicMock()]
        conn.execute.side_effect = side_effects

    return engine


class TestWaitForDatabase:
    def test_succeeds_immediately(self):
        """БД доступна сразу — никакой задержки, нет исключений."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("shared.startup.time.sleep") as mock_sleep:
            wait_for_database(engine, "test-service", attempts=5, delay_seconds=0.1)

        mock_sleep.assert_not_called()

    def test_retries_on_failure(self):
        """При нескольких ошибках делает повторные попытки."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # Первые 2 вызова бросают ошибку, третий — успех
        conn.execute.side_effect = [
            OperationalError("err", None, None),
            OperationalError("err", None, None),
            MagicMock(),
        ]

        with patch("shared.startup.time.sleep") as mock_sleep:
            wait_for_database(engine, "test-service", attempts=5, delay_seconds=0.5)

        # sleep должен быть вызван дважды (после каждой неудачной попытки)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    def test_raises_after_max_attempts(self):
        """После исчерпания попыток пробрасывает последнее исключение."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.side_effect = OperationalError("db down", None, None)

        with patch("shared.startup.time.sleep"):
            with pytest.raises(OperationalError):
                wait_for_database(engine, "test-service", attempts=3, delay_seconds=0.0)

    def test_respects_attempt_count(self):
        """Количество попыток подключения ровно `attempts`."""
        engine = MagicMock()
        conn = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.side_effect = OperationalError("err", None, None)

        with patch("shared.startup.time.sleep"):
            with pytest.raises(OperationalError):
                wait_for_database(engine, "svc", attempts=4, delay_seconds=0.0)

        assert engine.connect.call_count == 4
