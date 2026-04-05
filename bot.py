from aiogram import Bot
from config import settings

# Initialize Bot instance
# Use DefaultBotProperties for version 3.x if needed, but for simplicity:
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
