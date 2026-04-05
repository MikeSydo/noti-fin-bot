import logging
from aiohttp import web
from bot import bot

from services.oauth_service import process_oauth_callback, validate_oauth_state
from services.i18n import i18n
from app.keyboards.reply import get_main_menu

logger = logging.getLogger(__name__)


async def handle_notion_oauth(request: web.Request) -> web.Response:
    """Handle OAuth 2.0 callback from Notion."""
    code = request.query.get("code")
    state = request.query.get("state")
    error = request.query.get("error")

    if error:
        return web.Response(text=f"OAuth Error: {error}", status=400)

    if not code or not state:
        return web.Response(text="Missing 'code' or 'state' parameters", status=400)

    # Validate CSRF state token and get user ID
    telegram_id = await validate_oauth_state(state)
    if not telegram_id:
        return web.Response(text="Invalid or expired session. Please try connecting again from the bot.", status=400)

    # Process OAuth callback (exchange token, store everything, discover databases)
    success, has_dbs = await process_oauth_callback(code, telegram_id)

    if success:
        # Notify user in Telegram
        try:
            if has_dbs:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=i18n.get_text('msg_notion_connected_success', telegram_id),
                    reply_markup=await get_main_menu(telegram_id)
                )
            else:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=i18n.get_text('msg_notion_connected_no_dbs', telegram_id),
                )
        except Exception as e:
            logger.error(f"Failed to send success message to {telegram_id}: {e}")

        return web.Response(text="Notion integration successful! You can close this page and return to the Telegram bot.")
    else:
        # Notify user of failure
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=i18n.get_text('msg_notion_connect_failed', telegram_id)
            )
        except Exception as e:
            logger.error(f"Failed to send failure message to {telegram_id}: {e}")

        return web.Response(text="Failed to connect Notion. See bot messages for details.", status=400)


async def handle_health_check(request: web.Request) -> web.Response:
    """Simple health check endpoint."""
    return web.Response(text="OK")


def setup_webapp() -> web.Application:
    """Setup aiohttp web app for webhooks/callbacks."""
    app = web.Application()
    app.router.add_get('/notion-oauth-callback', handle_notion_oauth)
    app.router.add_get('/health', handle_health_check)
    return app
