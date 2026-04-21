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
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import Bot

dp = Dispatcher()


async def set_bot_commands():
    """Register bot commands visible in the Telegram menu for all supported languages."""
    # Define default commands (used if user language is not supported)
    default_commands = [
        BotCommand(command="start", description=i18n.get_text('cmd_start_desc', lang_code='en')),
        BotCommand(command="connect", description=i18n.get_text('cmd_connect_desc', lang_code='en')),
        BotCommand(command="disconnect", description=i18n.get_text('cmd_disconnect_desc', lang_code='en')),
        BotCommand(command="help", description=i18n.get_text('cmd_help_desc', lang_code='en')),
        BotCommand(command="cancel", description=i18n.get_text('cmd_cancel_desc', lang_code='en')),
        BotCommand(command="version", description=i18n.get_text('cmd_version_desc', lang_code='en')),
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    # Register localized commands for each supported language
    for lang in i18n.langs.keys():
        localized_commands = [
            BotCommand(command="start", description=i18n.get_text('cmd_start_desc', lang_code=lang)),
            BotCommand(command="connect", description=i18n.get_text('cmd_connect_desc', lang_code=lang)),
            BotCommand(command="disconnect", description=i18n.get_text('cmd_disconnect_desc', lang_code=lang)),
            BotCommand(command="help", description=i18n.get_text('cmd_help_desc', lang_code=lang)),
            BotCommand(command="cancel", description=i18n.get_text('cmd_cancel_desc', lang_code=lang)),
            BotCommand(command="version", description=i18n.get_text('cmd_version_desc', lang_code=lang)),
        ]
        await bot.set_my_commands(localized_commands, scope=BotCommandScopeDefault(), language_code=lang)

async def on_startup(bot: Bot):
    """Run layout initialization for the bot."""
    await init_db()
    await i18n.load_user_langs_from_db()
    await set_bot_commands()
    
    if settings.WEBHOOK_URL:
        webhook_url = f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url)
    logging.info(f"Bot startup completed. Environment: {settings.ENV_NAME}, Version: {settings.VERSION}")


async def on_shutdown(bot: Bot):
    """Clean up on shutdown."""
    if settings.WEBHOOK_URL:
        await bot.delete_webhook()
    logging.info("Bot stopped.")


async def main():
    """Main entry point — registers middleware, routers, and starts polling or webhooks."""
    if not settings.NOTION_CLIENT_ID or not settings.NOTION_CLIENT_SECRET or not settings.NOTION_REDIRECT_URI:
        logging.critical("Missing required Notion OAuth config in .env. Exiting.")
        return

    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    dp.include_router(manual.router)
    dp.include_router(receipt.router)
    dp.include_router(accounts.router)
    dp.include_router(expenses.router)
    dp.include_router(group_expenses.router)
    dp.include_router(reports.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = setup_webapp()

    if settings.WEBHOOK_URL:
        # Webhook mode
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        # Run webapp
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', settings.PORT)
        await site.start()
        logging.info(f"Webhook server running on port {settings.PORT}.")
        
        # Keep running
        await asyncio.Event().wait()
    else:
        # Polling mode
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', settings.PORT)
        await site.start()
        logging.info(f"Local web server running on port {settings.PORT}.")
        
        await bot.delete_webhook()
        await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass