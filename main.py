"""
main.py - Discord-бот для игры «Тетрадь» с поддержкой Railway.
"""
import discord
from discord import app_commands
import asyncio
import os
from aiohttp import web  # <-- новый импорт

from database import Database
from game import GameManager
from ui import MenuView

# Глобальные объекты
db = Database()
game_manager = GameManager(db)

# Инициализация бота
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# -------------------- Команды --------------------
@tree.command(name="menu", description="Открыть главное меню игры")
async def menu_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧮 Тетрадь по математике — мультиплеер",
        description="**Добро пожаловать!** Выберите действие:",
        color=0xADD8E6
    )
    # Можно добавить картинку-заглушку или убрать set_image
    # embed.set_image(url="https://i.imgur.com/MPk8qLm.png")
    view = MenuView(game_manager)
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="ход", description="Сделать ход в игре (координата, например A1)")
@app_commands.describe(coord="Координата клетки (буква + цифра, например B3)")
async def move_command(interaction: discord.Interaction, coord: str):
    user_id = interaction.user.id
    if not game_manager.is_in_game(user_id):
        await interaction.response.send_message("Вы не участвуете ни в одной игре.", ephemeral=True)
        return
    # Игроки должны ходить в ЛС бота, поэтому проверяем канал
    if interaction.guild is not None:
        await interaction.response.send_message(
            "Пожалуйста, используйте команду /ход в личных сообщениях с ботом.",
            ephemeral=True
        )
        return
    result, _ = await game_manager.make_move(user_id, coord)
    await interaction.response.send_message(result, ephemeral=False)

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
        "• Ходите по очереди через `/ход координата`.\n"
        "• Побеждает тот, кто первый заполнит строку, столбец или диагональ.\n"
        "• Игра ведётся в личных сообщениях бота."
    )
    embed = discord.Embed(title="📖 Правила", description=rules_text, color=0xADD8E6)
    await interaction.response.send_message(embed=embed)

# -------------------- События бота --------------------
@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов к работе.")
    # Подключаем БД
    await db.connect()
    # Синхронизируем слэш-команды глобально
    try:
        synced = await tree.sync()
        print(f"Синхронизировано {len(synced)} команд(ы)")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

    # ====== Для Railway: запускаем маленький HTTP-сервер ======
    app_web = web.Application()

    async def health_check(request):
        """Отвечает 'OK' на любой запрос к корню. Railway будет вызывать этот эндпоинт."""
        return web.Response(text="OK")

    app_web.add_routes([web.get('/', health_check)])

    runner = web.AppRunner(app_web)
    await runner.setup()
    # PORT передаётся Railway автоматически, по умолчанию 3000
    port = int(os.getenv('PORT', 3000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Health-check сервер запущен на порту {port}")

@bot.event
async def on_close():
    await db.close()

# -------------------- Точка входа --------------------
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Токен не найден. Установите переменную окружения DISCORD_TOKEN.")
    bot.run(token)