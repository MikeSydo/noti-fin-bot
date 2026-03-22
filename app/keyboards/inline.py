from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

async def get_skip_initial_amount_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Пропустити', callback_data='skip_initial_amount')]
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