import aiohttp
import logging
from aiohttp import web
from config import settings
from services.security import encrypt_token
from services.user_service import create_or_update_user

logger = logging.getLogger(__name__)

async def handle_notion_oauth(request: web.Request) -> web.Response:
    """Handle OAuth 2.0 callback from Notion."""
    code = request.query.get("code")
    state = request.query.get("state")  # Should contain Telegram User ID
    error = request.query.get("error")

    if error:
        return web.Response(text=f"OAuth Error: {error}", status=400)

    if not code or not state:
        return web.Response(text="Missing 'code' or 'state' parameters", status=400)

    try:
        telegram_id = int(state)
    except ValueError:
        return web.Response(text="Invalid 'state' parameter", status=400)

    # Exchange code for access token
    auth_url = "https://api.notion.com/v1/oauth/token"
    auth_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.NOTION_REDIRECT_URI
    }
    headers = {
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    basic_auth = aiohttp.BasicAuth(
        login=settings.NOTION_CLIENT_ID,
        password=settings.NOTION_CLIENT_SECRET
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(auth_url, json=auth_data, headers=headers, auth=basic_auth) as resp:
            response_data = await resp.json()

            if resp.status != 200:
                logger.error(f"Notion OAuth error: {response_data}")
                return web.Response(text=f"Failed to get token: {response_data.get('error')}", status=400)

            access_token = response_data.get("access_token")
            # Currently Notion appends duplicated template ids into the duplicated_template_id array.

            if access_token:
                encrypted_token = encrypt_token(access_token)

                # Fetch duplicated databases if provided down the line or just store access token
                await create_or_update_user(
                    telegram_id=telegram_id,
                    notion_access_token_encrypted=encrypted_token
                )

                return web.Response(text="Notion integration successful! You can close this page and return to the Telegram bot.")
            else:
                return web.Response(text="No access token received from Notion.", status=400)

def setup_webapp() -> web.Application:
    """Setup aiohttp web app for webhooks/callbacks."""
    app = web.Application()
    app.router.add_get('/notion-oauth-callback', handle_notion_oauth)
    return app

