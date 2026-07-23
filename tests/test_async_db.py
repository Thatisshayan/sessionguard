"""
tests/test_async_db.py
----------------------
Tests for async database helpers in database/db.py.
Verifies get_async_connection, async_fetch_one/all, async_execute/execute_many.
"""

import pytest
from database.db import (
    get_async_connection,
    async_fetch_one,
    async_fetch_all,
    async_execute,
    async_execute_many,
    init_db,
    get_connection,
)


@pytest.fixture(autouse=True)
def setup_db(test_db):
    """Ensure DB is initialized before tests, using the temp test DB."""
    init_db()


class TestAsyncConnection:
    """Tests for get_async_connection()."""

    @pytest.mark.asyncio
    async def test_returns_connection(self):
        """Should return an async connection object."""
        conn = await get_async_connection()
        assert conn is not None
        await conn.close()

    @pytest.mark.asyncio
    async def test_connection_has_row_factory(self):
        """Connection should have row_factory set."""
        conn = await get_async_connection()
        assert conn.row_factory is not None
        await conn.close()


class TestAsyncFetchOne:
    """Tests for async_fetch_one()."""

    @pytest.mark.asyncio
    async def test_fetch_one_returns_dict(self):
        """Should return a single row as dict."""
        result = await async_fetch_one("SELECT 1 AS val")
        assert result is not None
        assert result["val"] == 1

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none_on_no_match(self):
        """Should return None when no rows match."""
        result = await async_fetch_one("SELECT * FROM sessions WHERE id = ?", (999999,))
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_one_with_params(self):
        """Should handle parameterized queries."""
        result = await async_fetch_one(
            "SELECT ? AS a, ? AS b", ("hello", 42)
        )
        assert result["a"] == "hello"
        assert result["b"] == 42

    @pytest.mark.asyncio
    async def test_fetch_one_reads_sessions_table(self):
        """Should be able to query the sessions table."""
        result = await async_fetch_one("SELECT COUNT(*) AS cnt FROM sessions")
        assert result is not None
        assert "cnt" in result
        assert isinstance(result["cnt"], int)


class TestAsyncFetchAll:
    """Tests for async_fetch_all()."""

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self):
        """Should return a list of dicts."""
        results = await async_fetch_all("SELECT 1 AS val UNION SELECT 2 AS val")
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["val"] == 1
        assert results[1]["val"] == 2

    @pytest.mark.asyncio
    async def test_fetch_all_empty_result(self):
        """Should return empty list when no rows match."""
        results = await async_fetch_all(
            "SELECT * FROM sessions WHERE id = ?", (999999,)
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_all_reads_sessions(self):
        """Should be able to list sessions."""
        results = await async_fetch_all("SELECT id FROM sessions LIMIT 5")
        assert isinstance(results, list)


class TestAsyncExecute:
    """Tests for async_execute()."""

    @pytest.mark.asyncio
    async def test_execute_returns_lastrowid(self):
        """Should return lastrowid for INSERT."""
        lastrowid = await async_execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Test Session", "Test Game", "Test Platform", "2026-01-01", 100.0, 100.0)
        )
        assert lastrowid is not None
        assert lastrowid > 0

    @pytest.mark.asyncio
    async def test_execute_persists_data(self):
        """Inserted data should be readable."""
        session_id = await async_execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Async Test", "Game", "Platform", "2026-01-01", 50.0, 75.0)
        )
        result = await async_fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        assert result is not None
        assert result["name"] == "Async Test"
        assert result["start_balance"] == 50.0

    @pytest.mark.asyncio
    async def test_execute_update(self):
        """Should handle UPDATE queries."""
        session_id = await async_execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("Update Test", "Game", "Platform", "2026-01-01", 100.0, 100.0)
        )
        rowcount = await async_execute(
            "UPDATE sessions SET notes = ? WHERE id = ?",
            ("updated notes", session_id)
        )
        assert rowcount == 1
        result = await async_fetch_one("SELECT notes FROM sessions WHERE id = ?", (session_id,))
        assert result["notes"] == "updated notes"


class TestAsyncExecuteMany:
    """Tests for async_execute_many()."""

    @pytest.mark.asyncio
    async def test_execute_many_inserts_multiple_rows(self):
        """Should insert multiple rows at once."""
        params_list = [
            (f"Bulk Session {i}", "Game", "Platform", "2026-01-01", 100.0, 100.0)
            for i in range(5)
        ]
        rowcount = await async_execute_many(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            params_list
        )
        assert rowcount == 5

        count = await async_fetch_one("SELECT COUNT(*) AS cnt FROM sessions WHERE name LIKE 'Bulk Session%'")
        assert count["cnt"] == 5

    @pytest.mark.asyncio
    async def test_execute_many_empty_list(self):
        """Should handle empty params list gracefully."""
        rowcount = await async_execute_many(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            []
        )
        assert rowcount == 0
