import time
from typing import Any, Dict, List, Optional, Sequence

import aiosqlite

from bot.config import DATABASE_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS players (
                internal_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id         INTEGER UNIQUE,
                username      TEXT,
                nick          TEXT,
                is_banned     INTEGER DEFAULT 0,
                created_at    INTEGER
            );

            CREATE TABLE IF NOT EXISTS game_formats (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS limits (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS format_limits (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                format_id INTEGER NOT NULL,
                limit_id  INTEGER NOT NULL,
                UNIQUE (format_id, limit_id),
                FOREIGN KEY(format_id) REFERENCES game_formats(id) ON DELETE CASCADE,
                FOREIGN KEY(limit_id) REFERENCES limits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS segments (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                format_id INTEGER NOT NULL,
                limit_id  INTEGER NOT NULL,
                UNIQUE (format_id, limit_id),
                FOREIGN KEY(format_id) REFERENCES game_formats(id) ON DELETE CASCADE,
                FOREIGN KEY(limit_id) REFERENCES limits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS segment_assignments (
                player_id  INTEGER NOT NULL,
                segment_id INTEGER NOT NULL,
                UNIQUE (player_id, segment_id),
                FOREIGN KEY(player_id) REFERENCES players(internal_id) ON DELETE CASCADE,
                FOREIGN KEY(segment_id) REFERENCES segments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS requests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id  INTEGER NOT NULL,
                format_id  INTEGER NOT NULL,
                limit_id   INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(player_id) REFERENCES players(internal_id) ON DELETE CASCADE,
                FOREIGN KEY(format_id) REFERENCES game_formats(id) ON DELETE CASCADE,
                FOREIGN KEY(limit_id) REFERENCES limits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scheduled_deletions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                delete_at  INTEGER NOT NULL
            );
            """
        )
        await db.commit()


async def _fetchone(query: str, params: Sequence[Any] = ()) -> Optional[aiosqlite.Row]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()


async def _fetchall(query: str, params: Sequence[Any] = ()) -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def _execute(query: str, params: Sequence[Any] = ()) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(query, params)
        await db.commit()


# Players


async def get_or_create_player(tg_id: int, username: Optional[str]) -> Dict[str, Any]:
    row = await _fetchone("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    if row:
        return dict(row)

    created_at = int(time.time())
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO players (tg_id, username, created_at) VALUES (?, ?, ?)",
            (tg_id, username, created_at),
        )
        await db.commit()
        internal_id = cursor.lastrowid

    new_row = await _fetchone("SELECT * FROM players WHERE internal_id = ?", (internal_id,))
    return dict(new_row) if new_row else {}


async def update_player_username(tg_id: int, username: Optional[str]) -> None:
    await _execute("UPDATE players SET username = ? WHERE tg_id = ?", (username, tg_id))


async def get_player_by_internal_id(internal_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM players WHERE internal_id = ?", (internal_id,))
    return dict(row) if row else None


async def get_player_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    return dict(row) if row else None


async def get_player_by_any_id(identifier: int) -> Optional[Dict[str, Any]]:
    # Internal id has priority
    player = await get_player_by_internal_id(identifier)
    if player:
        return player
    return await get_player_by_tg_id(identifier)


async def set_player_nick(internal_id: int, nick: str) -> None:
    await _execute("UPDATE players SET nick = ? WHERE internal_id = ?", (nick, internal_id))


async def set_player_ban(internal_id: int, banned: bool) -> None:
    await _execute(
        "UPDATE players SET is_banned = ? WHERE internal_id = ?",
        (1 if banned else 0, internal_id),
    )


async def is_banned_by_tg_id(tg_id: int) -> bool:
    row = await _fetchone("SELECT is_banned FROM players WHERE tg_id = ?", (tg_id,))
    if not row:
        return False
    return bool(row["is_banned"])


# Formats and limits


async def add_format(name: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO game_formats (name) VALUES (?)",
            (name,),
        )
        await db.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
    row = await _fetchone("SELECT id FROM game_formats WHERE name = ?", (name,))
    return int(row["id"]) if row else 0


async def add_limit(name: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO limits (name) VALUES (?)",
            (name,),
        )
        await db.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
    row = await _fetchone("SELECT id FROM limits WHERE name = ?", (name,))
    return int(row["id"]) if row else 0


async def link_format_limit(format_id: int, limit_id: int) -> None:
    await _execute(
        "INSERT OR IGNORE INTO format_limits (format_id, limit_id) VALUES (?, ?)",
        (format_id, limit_id),
    )


async def get_all_formats() -> List[Dict[str, Any]]:
    rows = await _fetchall("SELECT id, name FROM game_formats ORDER BY id")
    return [dict(r) for r in rows]


async def get_limits_for_format(format_id: int) -> List[Dict[str, Any]]:
    rows = await _fetchall(
        """
        SELECT l.id, l.name
        FROM limits l
        JOIN format_limits fl ON fl.limit_id = l.id
        WHERE fl.format_id = ?
        ORDER BY l.id
        """,
        (format_id,),
    )
    return [dict(r) for r in rows]


async def get_format_by_id(format_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM game_formats WHERE id = ?", (format_id,))
    return dict(row) if row else None


async def get_limit_by_id(limit_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM limits WHERE id = ?", (limit_id,))
    return dict(row) if row else None


# Segments


async def get_or_create_segment(format_id: int, limit_id: int) -> int:
    row = await _fetchone(
        "SELECT id FROM segments WHERE format_id = ? AND limit_id = ?",
        (format_id, limit_id),
    )
    if row:
        return int(row["id"])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO segments (format_id, limit_id) VALUES (?, ?)",
            (format_id, limit_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_segment_by_pair(format_id: int, limit_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone(
        "SELECT * FROM segments WHERE format_id = ? AND limit_id = ?",
        (format_id, limit_id),
    )
    return dict(row) if row else None


async def assign_segment(player_id: int, segment_id: int) -> None:
    await _execute(
        "INSERT OR IGNORE INTO segment_assignments (player_id, segment_id) VALUES (?, ?)",
        (player_id, segment_id),
    )


async def unassign_segment(player_id: int, segment_id: int) -> None:
    await _execute(
        "DELETE FROM segment_assignments WHERE player_id = ? AND segment_id = ?",
        (player_id, segment_id),
    )


async def get_segments_for_player(player_id: int) -> List[int]:
    rows = await _fetchall(
        "SELECT segment_id FROM segment_assignments WHERE player_id = ? ORDER BY segment_id",
        (player_id,),
    )
    return [int(r["segment_id"]) for r in rows]


async def get_all_segments_with_names() -> List[Dict[str, Any]]:
    rows = await _fetchall(
        """
        SELECT s.id AS segment_id,
               s.format_id,
               s.limit_id,
               gf.name AS format_name,
               l.name  AS limit_name
        FROM segments s
        JOIN game_formats gf ON gf.id = s.format_id
        JOIN limits l ON l.id = s.limit_id
        ORDER BY s.id
        """
    )
    return [dict(r) for r in rows]


async def get_players_for_segment(segment_id: int, exclude_player_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if exclude_player_id is not None:
        rows = await _fetchall(
            """
            SELECT p.*
            FROM players p
            JOIN segment_assignments sa ON sa.player_id = p.internal_id
            WHERE sa.segment_id = ? AND p.internal_id <> ?
            """,
            (segment_id, exclude_player_id),
        )
    else:
        rows = await _fetchall(
            """
            SELECT p.*
            FROM players p
            JOIN segment_assignments sa ON sa.player_id = p.internal_id
            WHERE sa.segment_id = ?
            """,
            (segment_id,),
        )
    return [dict(r) for r in rows]


# Requests


async def create_request(player_id: int, format_id: int, limit_id: int) -> int:
    created_at = int(time.time())
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO requests (player_id, format_id, limit_id, created_at) VALUES (?, ?, ?, ?)",
            (player_id, format_id, limit_id, created_at),
        )
        await db.commit()
        return cursor.lastrowid


async def get_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM requests WHERE id = ?", (request_id,))
    return dict(row) if row else None


async def delete_request(request_id: int) -> None:
    await _execute("DELETE FROM requests WHERE id = ?", (request_id,))


# Scheduled deletions


async def schedule_deletion(chat_id: int, message_id: int, delete_at: int) -> None:
    await _execute(
        "INSERT INTO scheduled_deletions (chat_id, message_id, delete_at) VALUES (?, ?, ?)",
        (chat_id, message_id, delete_at),
    )


async def get_due_scheduled_deletions(now_ts: int) -> List[Dict[str, Any]]:
    rows = await _fetchall(
        "SELECT id, chat_id, message_id FROM scheduled_deletions WHERE delete_at <= ?",
        (now_ts,),
    )
    return [dict(r) for r in rows]


async def delete_scheduled_deletions(ids: List[int]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    query = f"DELETE FROM scheduled_deletions WHERE id IN ({placeholders})"
    await _execute(query, list(ids))

