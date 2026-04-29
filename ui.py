"""
ui.py - Представления (Views) для главного меню и игровой панели.
Теперь ходы делаются кнопками: выбираем столбец (кнопки A-H) и строку (1-8).
"""
import discord
from discord.ui import View, Button, button

class MenuView(View):
    def __init__(self, game_manager):
        super().__init__(timeout=None)
        self.gm = game_manager

    @button(label="🏆 Таблица лидеров", style=discord.ButtonStyle.primary, row=0)
    async def leaderboard_button(self, interaction: discord.Interaction, button: Button):
        from main import db
        top = await db.get_top(10)
        desc = ""
        for idx, (uid, wins, rating) in enumerate(top, start=1):
            user = interaction.client.get_user(uid) or await interaction.client.fetch_user(uid)
            name = user.name if user else f"ID {uid}"
            desc += f"`{idx}.` **{name}** — {wins} побед (рейтинг {rating})\n"
        embed = discord.Embed(title="🏆 Лидеры", description=desc or "Пока пусто", color=0xFFD700)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @button(label="🎮 Играть", style=discord.ButtonStyle.success, row=0)
    async def play_button(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        status = await self.gm.add_to_queue(user_id, interaction.channel_id)
        await interaction.response.send_message(status, ephemeral=True)

    @button(label="❓ Правила", style=discord.ButtonStyle.secondary, row=0)
    async def rules_button(self, interaction: discord.Interaction, button: Button):
        rules_text = (
            "**Правила игры «Тетрадь»**\n"
            "• Поле 8x8.\n"
            "• У каждого игрока уникальная фигура: 🔴, 🔺, 🟩, 🔹.\n"
            "• Ходите по очереди, выбирая клетку кнопками ниже.\n"
            "• Побеждает тот, кто первым заполнит строку, столбец или диагональ.\n"
            "• Игра идёт прямо в этом канале!"
        )
        embed = discord.Embed(title="📖 Правила", description=rules_text, color=0xADD8E6)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GameView(View):
    """Кнопки для хода: сначала выбирается столбец, потом строка."""
    def __init__(self, game, game_manager):
        super().__init__(timeout=300)  # завершится, если 5 минут не ходят
        self.game = game
        self.gm = game_manager
        self.selected_col: Optional[str] = None

        # Кнопки столбцов A-H
        for i, col in enumerate(COLUMNS):
            btn = Button(label=col, style=discord.ButtonStyle.secondary, row=0, custom_id=f"col_{col}")
            btn.callback = self.col_callback
            self.add_item(btn)

        # Кнопки строк 1-8 появятся после выбора столбца
        self.row_buttons_added = False

    async def col_callback(self, interaction: discord.Interaction):
        # Проверка, что ход делает правильный игрок
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message("Вы не участвуете в этой игре.", ephemeral=True)
            return
        if interaction.user.id != self.game.turn:
            await interaction.response.send_message("Сейчас не ваш ход.", ephemeral=True)
            return

        col = interaction.data["custom_id"].replace("col_", "")
        self.selected_col = col
        # Добавляем кнопки строк, если их ещё нет
        if not self.row_buttons_added:
            for r in ROWS:
                btn = Button(label=str(r), style=discord.ButtonStyle.primary, row=1, custom_id=f"row_{r}")
                btn.callback = self.row_callback
                self.add_item(btn)
            self.row_buttons_added = True
        # Обновляем сообщение: показываем, что столбец выбран
        embed = self.gm._game_embed(self.game, None)
        embed.set_footer(text=f"Выбран столбец {col}. Нажмите строку.")
        await interaction.response.edit_message(embed=embed, view=self)

    async def row_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.game.players:
            await interaction.response.send_message("Вы не участвуете в этой игре.", ephemeral=True)
            return
        if interaction.user.id != self.game.turn:
            await interaction.response.send_message("Сейчас не ваш ход.", ephemeral=True)
            return
        if self.selected_col is None:
            await interaction.response.send_message("Сначала выберите столбец.", ephemeral=True)
            return

        row = interaction.data["custom_id"].replace("row_", "")
        coord = f"{self.selected_col}{row}"
        # Сбрасываем выбор
        self.selected_col = None
        # Совершаем ход
        result, _ = await self.gm.make_move(interaction.user.id, coord)
        # После хода игра может завершиться, тогда view нужно убрать.
        if self.game.winner is not None:
            await interaction.response.edit_message(content=result, view=None)
            self.stop()
        else:
            # просто показываем новое состояние (сообщение уже отправлено в make_move)
            # но нужно обновить текущее сообщение
            await interaction.response.edit_message(content=result, view=self)