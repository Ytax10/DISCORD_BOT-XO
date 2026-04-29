"""
game.py - Управление игровыми сессиями: матчмейкинг, поле, ходы, победа.
"""
import asyncio
import random
from typing import Dict, Optional, List, Tuple
from discord import Member, User
import discord  # для бота внутри метода

SIZE = 8
COLUMNS = [chr(ord('A') + i) for i in range(SIZE)]
ROWS = list(range(1, SIZE + 1))

PIECES = ["🔴", "🔺", "🟩", "🔹"]
EMPTY_CELL = "⬜"

CLEANUP_DELAY = 60

class Game:
    def __init__(self, player1_id: int, player2_id: int, game_id: int):
        self.game_id = game_id
        self.players = {player1_id, player2_id}
        available = list(PIECES)
        random.shuffle(available)
        self.piece_of = {player1_id: available[0], player2_id: available[1]}
        self.grid: List[List[Optional[int]]] = [
            [None for _ in range(SIZE)] for _ in range(SIZE)
        ]
        self.turn: int = player1_id
        self.started = False
        self.winner: Optional[int] = None
        self.move_count = {player1_id: 0, player2_id: 0}
        self.cleanup_task: Optional[asyncio.Task] = None

    def cell_index(self, coord: str) -> Tuple[int, int]:
        coord = coord.upper().strip()
        if len(coord) < 2:
            raise ValueError("Слишком короткая координата")
        col_letter, row_part = coord[0], coord[1:]
        if col_letter not in COLUMNS:
            raise ValueError(f"Недопустимая колонка: {col_letter}")
        col_idx = COLUMNS.index(col_letter)
        try:
            row_num = int(row_part)
        except ValueError:
            raise ValueError("Номер ряда должен быть числом")
        if row_num not in ROWS:
            raise ValueError(f"Номер ряда вне диапазона 1..{SIZE}")
        row_idx = row_num - 1
        return row_idx, col_idx

    def place_piece(self, player_id: int, coord: str) -> str:
        if player_id not in self.players:
            raise ValueError("Вы не участвуете в этой игре")
        if self.winner is not None:
            raise ValueError("Игра уже завершена")
        if player_id != self.turn:
            raise ValueError("Сейчас не ваш ход")
        row, col = self.cell_index(coord)
        if self.grid[row][col] is not None:
            raise ValueError("Клетка уже занята")
        self.grid[row][col] = player_id
        self.move_count[player_id] += 1
        if self.check_win(player_id, row, col):
            self.winner = player_id
        else:
            other = next(p for p in self.players if p != player_id)
            self.turn = other
        return self.piece_of[player_id]

    def check_win(self, player_id: int, row: int, col: int) -> bool:
        if all(self.grid[row][c] == player_id for c in range(SIZE)):
            return True
        if all(self.grid[r][col] == player_id for r in range(SIZE)):
            return True
        if row == col:
            if all(self.grid[i][i] == player_id for i in range(SIZE)):
                return True
        if row + col == SIZE - 1:
            if all(self.grid[i][SIZE - 1 - i] == player_id for i in range(SIZE)):
                return True
        return False

    def render_board(self) -> str:
        lines = ["`" + " ".join(COLUMNS) + "`"]
        for r_idx in range(SIZE):
            row_cells = []
            for c_idx in range(SIZE):
                pid = self.grid[r_idx][c_idx]
                if pid is None:
                    row_cells.append(EMPTY_CELL)
                else:
                    row_cells.append(self.piece_of[pid])
            lines.append(f"`{r_idx+1}`" + "".join(row_cells))
        return "\n".join(lines)

    def stats_message(self) -> str:
        p1, p2 = list(self.players)
        return (
            f"Игрок {p1}: {self.move_count[p1]} клеток\n"
            f"Игрок {p2}: {self.move_count[p2]} клеток"
        )

class GameManager:
    def __init__(self, db):
        self.queue: List[int] = []
        self.active_games: Dict[int, Game] = {}
        self.player_game: Dict[int, int] = {}
        self._game_id_counter = 0
        self.db = db

    async def add_to_queue(self, user_id: int) -> str:
        if user_id in self.player_game:
            return "Вы уже находитесь в игре."
        if user_id in self.queue:
            return "Вы уже в очереди на поиск соперника."
        self.queue.append(user_id)
        if len(self.queue) >= 2:
            p1 = self.queue.pop(0)
            p2 = self.queue.pop(0)
            self._game_id_counter += 1
            game = Game(p1, p2, self._game_id_counter)
            self.active_games[game.game_id] = game
            self.player_game[p1] = game.game_id
            self.player_game[p2] = game.game_id
            game.started = True
            asyncio.create_task(self._notify_game_start(game))
            return "Соперник найден! Игра начинается."
        else:
            return "Вы в очереди. Ожидайте соперника..."

    async def remove_from_queue(self, user_id: int) -> str:
        if user_id in self.queue:
            self.queue.remove(user_id)
            return "Вы покинули очередь."
        return "Вас нет в очереди."

    async def _notify_game_start(self, game: Game):
        # здесь нужен доступ к боту; мы используем глобальный объект из main
        from main import bot
        for pid in game.players:
            user = bot.get_user(pid) or await bot.fetch_user(pid)
            if user:
                embed = self._game_embed(game, pid)
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass

    def _game_embed(self, game: Game, user_id: int):
        embed = discord.Embed(
            title="🧮 Мультиплеерная тетрадь",
            description=game.render_board(),
            color=0xADD8E6
        )
        piece = game.piece_of[user_id]
        embed.add_field(name="Ваша фигура", value=piece, inline=True)
        if game.winner is None:
            turn_mention = f"<@{game.turn}>"
            embed.add_field(name="Ход", value=turn_mention, inline=True)
            embed.set_footer(text="Введите /ход координата (например A1)")
        else:
            embed.add_field(name="Победитель", value=f"<@{game.winner}>", inline=True)
        return embed

    async def make_move(self, user_id: int, coord: str):
        game_id = self.player_game.get(user_id)
        if game_id is None:
            return "Вы не в игре.", None
        game = self.active_games.get(game_id)
        if game is None:
            return "Игра не найдена.", None
        try:
            piece = game.place_piece(user_id, coord)
        except ValueError as e:
            return str(e), None
        # Отправляем обновлённую доску обоим
        from main import bot
        for pid in game.players:
            user = bot.get_user(pid) or await bot.fetch_user(pid)
            if user:
                embed = self._game_embed(game, pid)
                try:
                    await user.send(embed=embed)
                except:
                    pass
        if game.winner is not None:
            await self._end_game(game)
            return f"Вы поставили {piece} на {coord}. Вы победили!", None
        return f"Вы поставили {piece} на {coord}. Ход передан сопернику.", game

    async def _end_game(self, game: Game):
        if game.winner is not None:
            await self.db.add_win(game.winner)
        async def cleanup():
            await asyncio.sleep(CLEANUP_DELAY)
            self.active_games.pop(game.game_id, None)
            for pid in game.players:
                self.player_game.pop(pid, None)
        game.cleanup_task = asyncio.create_task(cleanup())

    def is_in_game(self, user_id: int) -> bool:
        return user_id in self.player_game