from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from models.account import Account
from models.category import Category


async def get_skip_attribute_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Пропустити', callback_data='skip_attribute')]
        ],
    )

async def get_accounts_keyboard(accounts: list[Account]) -> InlineKeyboardMarkup:
    keyboard = []
    for account in accounts:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{account.name} ({account.initial_amount or 0:.2f})",
                callback_data=f"select_account_{account.id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_today_date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Сьогоднішня дата', callback_data='today_date')]
        ]
    )

async def get_categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    keyboard = []
    for category in categories:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{category.name} ({category.monthly_budget or 0:.2f})",
                callback_data=f"select_category_{category.id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)