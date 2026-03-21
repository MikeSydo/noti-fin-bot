import asyncio
import logging

from aiogram import Dispatcher, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN,)
dp = Dispatcher() #router to process messages, callback, etc...

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Hello!')


async def main():
    await dp.start_polling(bot) #send request to telegram server

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass