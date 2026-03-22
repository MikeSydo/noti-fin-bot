from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

async def get_skip_initial_amount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Пропустити', callback_data='skip_initial_amount')]
        ],
    )