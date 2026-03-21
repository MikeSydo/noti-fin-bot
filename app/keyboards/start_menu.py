from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

async def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Додати витрату')],
            [KeyboardButton(text='Аналітика')],
            [KeyboardButton(text='Допомога')]
        ],
        resize_keyboard=True,
    )