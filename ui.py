"""
ui.py - Представления (Views) для главного меню и, при необходимости, игровых панелей.
"""
import discord
from discord.ui import View, Button

class MenuView(View):
    def __init__(self, game_manager):
        super().__init__(timeout=None)
        self.gm = game_manager

    @discord.ui.button(label="🏆 Таблица лидеров", style=discord.ButtonStyle.primary, row=0)
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

    @discord.ui.button(label="🎮 Играть", style=discord.ButtonStyle.success, row=0)
    async def play_button(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        status = await self.gm.add_to_queue(user_id)
        if status == "Соперник найден! Игра начинается.":
            await interaction.response.send_message("Соперник найден! Игра начинается в личных сообщениях.", ephemeral=True)
        else:
            await interaction.response.send_message(status, ephemeral=True)

    @discord.ui.button(label="❓ Правила", style=discord.ButtonStyle.secondary, row=0)
    async def rules_button(self, interaction: discord.Interaction, button: Button):
        rules_text = (
            "**Правила игры «Тетрадь»**\n"
            "• Поле 8x8, как лист тетради.\n"
            "• У каждого игрока уникальная фигура: 🔴, 🔺, 🟩, 🔹.\n"
            "• Ходите по очереди, указывая клетку (например, `A1`).\n"
            "• Побеждает тот, кто первым заполнит своей фигурой **всю строку, весь столбец или одну из двух главных диагоналей**.\n"
            "• Используйте команду `/ход координата` в личных сообщениях с ботом.\n"
            "• За победу начисляются очки в таблицу лидеров."
        )
        embed = discord.Embed(title="📖 Правила", description=rules_text, color=0xADD8E6)
        await interaction.response.send_message(embed=embed, ephemeral=True)