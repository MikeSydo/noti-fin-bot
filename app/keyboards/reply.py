from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

async def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Додати акаунт'), KeyboardButton(text='Видалити акаунт')],
            [KeyboardButton(text='Додати витрату')],
            [KeyboardButton(text='Аналітика')],
            [KeyboardButton(text='Допомога')]
        ],
        resize_keyboard=True,
    )