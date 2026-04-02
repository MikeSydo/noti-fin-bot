from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.account import Account
from models.category import Category
from models.expense import Expense
from models.group_expense import GroupExpense


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

async def get_expenses_keyboard(expenses: list[Expense], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    start_idx = page * 5
    end_idx = start_idx + 5
    current_expenses = expenses[start_idx:end_idx]
    
    for expense in current_expenses:
        # Format date for better display, e.g. YYYY-MM-DD
        date_str = expense.date[:10] if isinstance(expense.date, str) else expense.date.strftime("%Y-%m-%d")
        builder.add(
            InlineKeyboardButton(
                text=f"{expense.name} ({expense.amount or 0:.2f} | {date_str})",
                callback_data=f"select_expense_{expense.id}"
            )
        )
    # 1 button per row gives more horizontal space to prevent truncation
    builder.adjust(1)
    
    # Add navigation buttons if needed
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"exp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text="Вперед", callback_data=f"exp_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    return builder.as_markup()

async def get_group_expenses_keyboard(expenses: list[GroupExpense], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    start_idx = page * 5
    end_idx = start_idx + 5
    current_expenses = expenses[start_idx:end_idx]

    for expense in current_expenses:
        date_str = expense.date[:10] if isinstance(expense.date, str) else expense.date.strftime("%Y-%m-%d")
        builder.add(
            InlineKeyboardButton(
                text=f"{expense.name} ({expense.amount or 0:.2f} | {date_str})",
                callback_data=f"select_grexpense_{expense.id}"
            )
        )
    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"grexp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text="Вперед", callback_data=f"grexp_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()

async def get_multi_select_expenses_keyboard(expenses: list[Expense], selected_ids: set[str], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    start_idx = page * 5
    end_idx = start_idx + 5
    current_expenses = expenses[start_idx:end_idx]

    for expense in current_expenses:
        # Format date for better display, e.g. DD-MM-YYYY
        date_str = expense.date[:10] if isinstance(expense.date, str) else expense.date.strftime("%d-%m-%Y")
        is_selected = expense.id in selected_ids
        check_icon = "[ ]" if is_selected else "[*]"
        
        builder.add(
            InlineKeyboardButton(
                text=f"{check_icon} {expense.name} ({expense.amount or 0:.2f} | {date_str})",
                callback_data=f"toggle_grexpense_rel_{expense.id}"
            )
        )
    # 1 button per row gives more horizontal space
    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"multiexp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text="Вперед", callback_data=f"multiexp_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="Зберегти", callback_data="finish_expenses_selection"))

    return builder.as_markup()

async def get_skip_receipt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Пропустити', callback_data='skip_receipt')]
        ],
    )
