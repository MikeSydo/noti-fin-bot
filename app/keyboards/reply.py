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
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.get_text('btn_cancel', user_id))]
        ],
        resize_keyboard=True
    )
    return kb

async def get_language_menu() -> ReplyKeyboardMarkup:
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

async def get_analytics_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Creates and returns the analytics menu keyboard."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.get_text('menu_stats', user_id)),
                KeyboardButton(text=i18n.get_text('menu_comparison', user_id))
            ],
            [
                KeyboardButton(text=i18n.get_text('menu_analytics_main_menu', user_id))
            ]
        ],
        resize_keyboard=True
    )
    return kb

async def get_comparison_periods_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Creates and returns the period selection menu for comparison."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.get_text('menu_today', user_id)),
                KeyboardButton(text=i18n.get_text('menu_this_week', user_id)),
                KeyboardButton(text=i18n.get_text('menu_this_month', user_id))
            ],
            [
                KeyboardButton(text=i18n.get_text('menu_cancel', user_id))
            ]
        ],
        resize_keyboard=True
    )
    return kb
