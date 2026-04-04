import asyncio
import logging

from aiogram import Dispatcher, Bot
from config import settings
from app.handlers import manual, receipt, accounts, expenses, group_expenses, reports
from aiogram.types import BotCommand
from database import init_db
from services.i18n import i18n
from webapp import setup_webapp
from aiohttp import web

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher() #router to process messages, callback, etc...

async def set_bot_commands():
    """Set bot commands in the Telegram menu."""
    commands = [
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="help", description="Довідка"),
        BotCommand(command="cancel", description="Скасувати"),
    ]
    await bot.set_my_commands(commands)

async def start_web_server():
    """Start an internal web server for OAuth and Webhooks."""
    app = setup_webapp()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logging.info("Aiohttp internal WebServer is running on port 8080.")

async def main():
    """Main function - start polling."""
    await init_db()

    await i18n.load_user_langs_from_db()

    dp.include_router(manual.router)
    dp.include_router(receipt.router)
    dp.include_router(accounts.router)
    dp.include_router(expenses.router)
    dp.include_router(group_expenses.router)
    dp.include_router(reports.router)

    await set_bot_commands()

    await dp.start_polling(bot) #send request to telegram server

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass