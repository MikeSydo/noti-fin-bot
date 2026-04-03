from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

async def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Додати акаунт'), KeyboardButton(text='Видалити акаунт')],
            [KeyboardButton(text='Додати витрату'), KeyboardButton(text='Видалити витрату')],
            [KeyboardButton(text='Додати групову витрату'), KeyboardButton(text='Видалити групову витрату')],
            [KeyboardButton(text='Аналітика')],
            [KeyboardButton(text='Допомога')]
        ],
        resize_keyboard=True,
    )

async def get_analytics_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 Статистика'), KeyboardButton(text='⚖️ Порівняння')],
            [KeyboardButton(text='⬅️ Головне меню')]
        ],
        resize_keyboard=True,
    )

async def get_comparison_periods_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Цей день')],
            [KeyboardButton(text='Цей тиждень')],
            [KeyboardButton(text='Цей місяць')],
            [KeyboardButton(text='⬅️ Скасувати')]
        ],
        resize_keyboard=True,
    )
