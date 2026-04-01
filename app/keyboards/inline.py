from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.account import Account
from models.category import Category
from models.expenses import Expense


async def get_skip_attribute_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Пропустити', callback_data='skip_attribute')]
        ],
    )

async def get_accounts_keyboard(accounts: list[Account], include_skip: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if include_skip:
        builder.add(InlineKeyboardButton(text='Пропустити', callback_data='skip_account'))
        
    for account in accounts:
        builder.add(
            InlineKeyboardButton(
                text=f"{account.name} ({account.initial_amount or 0:.2f})",
                callback_data=f"select_account_{account.id}"
            )
        )
        
    sizes = [1, 2] if include_skip else [2]
    builder.adjust(*sizes)
    return builder.as_markup()

async def get_today_date_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Сьогоднішня дата', callback_data='today_date')]
        ]
    )

async def get_categories_keyboard(categories: list[Category], include_skip: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if include_skip:
        builder.add(InlineKeyboardButton(text='Пропустити', callback_data='skip_category'))
        
    for category in categories:
        builder.add(
            InlineKeyboardButton(
                text=f"{category.name} ({category.monthly_budget or 0:.2f})",
                callback_data=f"select_category_{category.id}"
            )
        )
        
    sizes = [1, 2] if include_skip else [2]
    builder.adjust(*sizes)
    return builder.as_markup()

async def get_expenses_keyboard(expenses: list[Expense]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for expense in expenses:
        builder.add(
            InlineKeyboardButton(
                text=f"{expense.name} ({expense.amount or 0:.2f})",
                callback_data=f"select_expense_{expense.id}"
            )
        )
    builder.adjust(2)
    return builder.as_markup()
