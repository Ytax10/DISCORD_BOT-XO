"""
database.py - Асинхронная обёртка над SQLite для учёта игроков.
Используем aiosqlite для неблокирующих операций.
"""
import aiosqlite
from typing import Optional, List, Tuple

DB_PATH = "game.db"

class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Открываем соединение (вызывается при старте бота)."""
        self.conn = await aiosqlite.connect(DB_PATH)
        # Включаем WAL-режим для быстрой параллельной записи
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                wins INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000
            );
        """)
        await self.conn.commit()

    async def close(self):
        """Закрываем соединение (вызывается при остановке бота)."""
        if self.conn:
            await self.conn.close()

    async def get_user(self, user_id: int) -> Tuple[int, int, int]:
        """Получить (user_id, wins, rating) или создать запись с нулями."""
        async with self.conn.execute(
            "SELECT wins, rating FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                await self.conn.execute(
                    "INSERT INTO users (user_id) VALUES (?)", (user_id,)
                )
                await self.conn.commit()
                return user_id, 0, 1000
            return user_id, row[0], row[1]

    async def add_win(self, user_id: int):
        """Добавить 1 победу и немного рейтинга."""
        user_id, wins, rating = await self.get_user(user_id)
        new_wins = wins + 1
        await self.conn.execute(
            "UPDATE users SET wins = ?, rating = ? WHERE user_id = ?",
            (new_wins, rating + 10, user_id)
        )
        await self.conn.commit()

    async def get_top(self, limit: int = 10) -> List[Tuple[int, int, int]]:
        """Топ-N игроков по количеству побед (убывание)."""
        async with self.conn.execute(
            "SELECT user_id, wins, rating FROM users ORDER BY wins DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()