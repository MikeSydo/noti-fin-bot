from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)
from services.i18n import i18n

async def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Creates and returns the main menu keyboard."""

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.get_text('btn_add_expense', user_id)),
                KeyboardButton(text=i18n.get_text('btn_del_expense', user_id)),
            ],
            [
                KeyboardButton(text=i18n.get_text('btn_add_group_expense', user_id)),
                KeyboardButton(text=i18n.get_text('btn_del_group_expense', user_id))
            ],
            [
                KeyboardButton(text=i18n.get_text('btn_add_account', user_id)),
                KeyboardButton(text=i18n.get_text('btn_del_account', user_id))
            ],
            [
                KeyboardButton(text=i18n.get_text('btn_analytics', user_id)),
            ],
            [
                KeyboardButton(text=i18n.get_text('btn_change_language', user_id))
            ]
        ],
        resize_keyboard=True
    )
    return kb

async def get_cancel_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Returns a simple cancel keyboard."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.get_text('btn_cancel', user_id))]
        ],
        resize_keyboard=True
    )
    return kb

async def get_language_menu() -> ReplyKeyboardMarkup:
    """Returns a language selection keyboard."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🇺🇦 Українська"),
                KeyboardButton(text="🇬🇧 English")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb
