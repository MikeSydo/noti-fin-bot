from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.account import Account
from models.category import Category
from models.expense import Expense
from models.group_expense import GroupExpense
from services.i18n import i18n


async def get_skip_attribute_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Returns an inline keyboard with a 'skip' button."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.get_text('btn_skip', user_id), callback_data="skip_attribute")]
        ]
    )
    return kb

async def get_accounts_keyboard(accounts: list[Account], include_skip: bool = False, user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if include_skip:
        builder.add(InlineKeyboardButton(text=i18n.get_text('btn_skip', user_id), callback_data='skip_account'))

    for account in accounts:
        budget_str = f"({account.monthly_budget:.2f})" if getattr(account, 'monthly_budget', None) else ""
        text_display = f"{account.name} {budget_str}".strip()
        builder.add(
            InlineKeyboardButton(
                text=text_display,
                callback_data=f"select_account_{account.id}"
            )
        )

    builder.adjust(1)
    return builder.as_markup()

async def get_today_date_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.get_text('btn_today_date', user_id), callback_data='today_date')]
        ]
    )

async def get_categories_keyboard(categories: list[Category], include_skip: bool = False, user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if include_skip:
        builder.add(InlineKeyboardButton(text=i18n.get_text('btn_skip', user_id), callback_data='skip_category'))

    for category in categories:
        builder.add(
            InlineKeyboardButton(
                text=f"{category.name}",
                callback_data=f"select_category_{category.id}"
            )
        )

    sizes = [1, 2] if include_skip else [2]
    builder.adjust(*sizes)
    return builder.as_markup()

async def get_expenses_keyboard(expenses: list[Expense], page: int, user_id: int = None) -> InlineKeyboardMarkup:
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
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_back', user_id), callback_data=f"exp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_forward', user_id), callback_data=f"exp_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)
        
    return builder.as_markup()

async def get_group_expenses_keyboard(expenses: list[GroupExpense], page: int, user_id: int = None) -> InlineKeyboardMarkup:
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
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_back', user_id), callback_data=f"grexp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_forward', user_id), callback_data=f"grexp_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()

async def get_multi_select_expenses_keyboard(expenses: list[Expense], selected_ids: set[str], page: int, user_id: int = None) -> InlineKeyboardMarkup:
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
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_back', user_id), callback_data=f"multiexp_page_{page-1}"))
    if end_idx < len(expenses):
        nav_buttons.append(InlineKeyboardButton(text=i18n.get_text('btn_forward', user_id), callback_data=f"multiexp_page_{page+1}"))

    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text=i18n.get_text('btn_save', user_id), callback_data="finish_expenses_selection"))

    return builder.as_markup()

async def get_years_inline_keyboard(years: list[int], prefix: str, user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for y in years:
        builder.add(InlineKeyboardButton(text=str(y), callback_data=f"{prefix}_{y}"))
    builder.adjust(3)
    return builder.as_markup()

async def get_months_inline_keyboard(prefix: str, user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    months = i18n.get_text('graph_months', user_id)
    for i, m in enumerate(months, start=1):
        builder.add(InlineKeyboardButton(text=m, callback_data=f"{prefix}_{i}"))
    builder.adjust(3)
    return builder.as_markup()

async def get_skip_receipt_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.get_text('btn_skip', user_id), callback_data='skip_receipt')]
        ],
    )
