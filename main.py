import asyncio
import logging

from aiohttp import web
from aiogram import Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot import bot
from config import settings
from db import init_db
from webapp import setup_webapp
from services.i18n import i18n
from app.handlers import manual, receipt, accounts, expenses, group_expenses, reports
from app.middleware.auth import AuthMiddleware

dp = Dispatcher()


async def set_bot_commands():
    """Register bot commands visible in the Telegram menu."""
    commands = [
        BotCommand(command="start"),
        BotCommand(command="connect"),
        BotCommand(command="disconnect"),
        BotCommand(command="help"),
        BotCommand(command="cancel"),
        BotCommand(command="version"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def start_web_server():
    """Start an internal web server for OAuth callbacks and health checks."""
    app = setup_webapp()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', settings.PORT)
    await site.start()
    logging.info(f"Web server running on port {settings.PORT}.")


async def main():
    """Main entry point — registers middleware, routers, and starts polling."""
    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET or not settings.NOTION_REDIRECT_URI:
        logging.critical("Missing required Notion OAuth config in .env. Exiting.")
        return

    await init_db()
    await i18n.load_user_langs_from_db()

    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    dp.include_router(manual.router)
    dp.include_router(receipt.router)
    dp.include_router(accounts.router)
    dp.include_router(expenses.router)
    dp.include_router(group_expenses.router)
    dp.include_router(reports.router)

    await set_bot_commands()
    logging.info(f"Bot started. Environment: {settings.ENV_NAME}, Version: {settings.VERSION}")

    asyncio.create_task(start_web_server())

    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass