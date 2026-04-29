"""
main.py - Discord-бот для игры «Тетрадь» с интерфейсом на кнопках.
Игра запускается прямо в канале, ходы через кнопки.
"""
import discord
from discord import app_commands
import os
from aiohttp import web

from database import Database
from game import GameManager, Game
from ui import MenuView, GameView

db = Database()
game_manager = GameManager(db)

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ------------- Команды -------------
@tree.command(name="menu", description="Открыть главное меню игры")
async def menu_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧮 Тетрадь по математике — мультиплеер",
        description="**Добро пожаловать!** Выберите действие:",
        color=0xADD8E6
    )
    view = MenuView(game_manager)
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="leaderboard", description="Показать таблицу лидеров")
async def leaderboard_command(interaction: discord.Interaction):
    top = await db.get_top(10)
    desc = ""
    for idx, (uid, wins, rating) in enumerate(top, start=1):
        user = bot.get_user(uid) or await bot.fetch_user(uid)
        name = user.name if user else f"ID {uid}"
        desc += f"`{idx}.` **{name}** — {wins} побед (рейтинг {rating})\n"
    embed = discord.Embed(title="🏆 Лидеры", description=desc or "Пока пусто", color=0xFFD700)
    await interaction.response.send_message(embed=embed)

@tree.command(name="rules", description="Правила игры")
async def rules_command(interaction: discord.Interaction):
    rules_text = (
        "**Правила игры «Тетрадь»**\n"
        "• Поле 8x8.\n"
        "• У каждого игрока уникальная фигура: 🔴, 🔺, 🟩, 🔹.\n"
        "• Ходите по очереди, выбирая клетку кнопками под игровым сообщением.\n"
        "• Побеждает тот, кто первым заполнит строку, столбец или диагональ.\n"
        "• Игра идёт прямо в канале, где была запущена."
    )
    embed = discord.Embed(title="📖 Правила", description=rules_text, color=0xADD8E6)
    await interaction.response.send_message(embed=embed)

# ------------- События бота -------------
@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов к работе.")
    await db.connect()
    try:
        synced = await tree.sync()
        print(f"Синхронизировано {len(synced)} команд(ы)")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

    # Health-check сервер для хостинга
    app_web = web.Application()
    async def health_check(request):
        return web.Response(text="OK")
    app_web.add_routes([web.get('/', health_check)])
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.getenv('PORT', 3000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Health-check сервер запущен на порту {port}")

@bot.event
async def on_close():
    await db.close()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Токен не найден. Установите переменную окружения DISCORD_TOKEN.")
    bot.run(token)