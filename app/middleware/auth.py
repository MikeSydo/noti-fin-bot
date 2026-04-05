import logging
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from services.notion_writer import get_notion_writer
from services.user_service import get_user
from services.i18n import i18n

logger = logging.getLogger(__name__)

# Commands that don't require Notion connection
BYPASS_COMMANDS = {"/start", "/help", "/cancel", "/connect", "/disconnect"}

# Button texts that don't require Notion (language selection)
BYPASS_BUTTON_PREFIXES = ("🇺🇦", "🇬🇧", "❌", "⬅️")


class AuthMiddleware(BaseMiddleware):
    """
    Outer middleware that checks if a user has a connected Notion account.
    If connected, injects `notion_writer` into handler data.
    If not connected, sends a message asking the user to connect.
    Bypasses check for /start, /help, /cancel, /connect, /disconnect.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Extract user_id from different event types
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None

            # Check if this is a bypass command or button
            if event.text:
                # Bypass for commands
                if event.text.split()[0].lower() in BYPASS_COMMANDS:
                    return await handler(event, data)

                # Bypass for language selection buttons
                if event.text.startswith(BYPASS_BUTTON_PREFIXES):
                    return await handler(event, data)

                # Bypass for "change language" button (all translations)
                change_lang_texts = i18n.get_all_translations('btn_change_language')
                if event.text in change_lang_texts:
                    return await handler(event, data)

            # Bypass for photo messages in default state (receipt scanning needs connection though)
            # Photos still need authentication

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if not user_id:
            return await handler(event, data)

        # Check if user has connected Notion
        user = await get_user(user_id)
        if not user or not user.is_notion_connected or not user.has_databases:
            # User needs to connect Notion first
            if isinstance(event, Message):
                await event.answer(
                    i18n.get_text('msg_notion_not_connected', user_id),
                    parse_mode="Markdown",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    i18n.get_text('msg_notion_not_connected_short', user_id),
                    show_alert=True,
                )
            return  # Stop processing

        # Create per-user NotionWriter and inject into handler data
        writer = await get_notion_writer(user_id)
        if not writer:
            if isinstance(event, Message):
                await event.answer(i18n.get_text('msg_notion_error', user_id))
            return

        data["notion_writer"] = writer
        return await handler(event, data)
