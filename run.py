import asyncio
import logging

from aiogram import Dispatcher, Bot
from config import settings
from app.handlers import manual, receipt
from aiogram.types import BotCommand

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher() #router to process messages, callback, etc...

async def set_bot_commands():
    """Set bot commands in the Telegram menu."""
    commands = [
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="help", description="Допомога"),
        BotCommand(command="cancel", description="Скасувати"),
    ]
    await bot.set_my_commands(commands)

async def main():
    """Main function - start polling."""
    dp.include_router(manual.router)
    dp.include_router(receipt.router)

    await set_bot_commands()

    await dp.start_polling(bot) #send request to telegram server

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass