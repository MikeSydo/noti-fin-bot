import logging
import asyncio
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
        return web.Response(
            text="Invalid or expired session. Please try connecting again from the bot.", 
            status=400
        )

    # Step 1: Exchange code for tokens (Fast)
    from services.oauth_service import complete_oauth_discovery
    success, token_response = await process_oauth_callback(code, telegram_id)

    if success:
        # Step 2: Start heavy discovery in the background (Async)
        asyncio.create_task(complete_oauth_discovery(token_response, telegram_id))

        # Return styled HTML success page immediately
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Notion Connected!</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f4f4f9;
                    color: #333;
                    text-align: center;
                }
                .container {
                    padding: 2rem;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    max-width: 400px;
                }
                h1 { color: #000; margin-bottom: 1rem; }
                p { line-height: 1.5; color: #666; }
                .icon { font-size: 3rem; margin-bottom: 1rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1>Notion Connected!</h1>
                <p>Authentication successful. We are now setting up your databases in the background.</p>
                <p><strong>You can safely close this window and return to your Telegram bot.</strong></p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
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
