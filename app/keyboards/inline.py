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

async def get_accounts_keyboard(accounts: list[Account], include_skip: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    if include_skip:
        keyboard.append([InlineKeyboardButton(text='Пропустити', callback_data='skip_account')])
    
    row = []
    for account in accounts:
        row.append(
            InlineKeyboardButton(
                text=f"{account.name} ({account.initial_amount or 0:.2f})",
                callback_data=f"select_account_{account.id}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_today_date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Сьогоднішня дата', callback_data='today_date')]
        ]
    )

async def get_categories_keyboard(categories: list[Category], include_skip: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    if include_skip:
        keyboard.append([InlineKeyboardButton(text='Пропустити', callback_data='skip_category')])
    
    row = []
    for category in categories:
        row.append(
            InlineKeyboardButton(
                text=f"{category.name} ({category.monthly_budget or 0:.2f})",
                callback_data=f"select_category_{category.id}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)