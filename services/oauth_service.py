import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
from config import settings
from services.security import encrypt_token, decrypt_token
from services.user_service import get_user, create_or_update_user, get_user_by_oauth_state

logger = logging.getLogger(__name__)

# OAuth state tokens expire after 10 minutes
OAUTH_STATE_TTL = timedelta(minutes=10)


async def generate_oauth_url(telegram_id: int) -> str:
    """
    Generate a Notion OAuth authorization URL with CSRF protection.
    Stores a random state token in the database tied to the user's telegram_id.
    """
    state_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + OAUTH_STATE_TTL

    await create_or_update_user(
        telegram_id=telegram_id,
        oauth_state=state_token,
        oauth_state_expires=expires_at,
    )

    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={settings.NOTION_CLIENT_ID}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={settings.NOTION_REDIRECT_URI}"
        f"&state={state_token}"
    )
    return auth_url


async def validate_oauth_state(state: str) -> Optional[int]:
    """
    Validate a CSRF state token from OAuth callback.
    Returns telegram_id if valid, None otherwise.
    Clears the state after successful validation (one-time use).
    """
    user = await get_user_by_oauth_state(state)
    if not user:
        logger.warning(f"OAuth state not found: {state[:8]}...")
        return None

    # Check expiration
    if user.oauth_state_expires and user.oauth_state_expires < datetime.now(timezone.utc):
        logger.warning(f"OAuth state expired for user {user.telegram_id}")
        # Clear expired state
        await create_or_update_user(
            telegram_id=user.telegram_id,
            oauth_state=None,
            oauth_state_expires=None,
        )
        return None

    # Clear state (one-time use)
    await create_or_update_user(
        telegram_id=user.telegram_id,
        oauth_state=None,
        oauth_state_expires=None,
    )

    return user.telegram_id


async def exchange_code_for_tokens(code: str) -> Optional[dict]:
    """
    Exchange an authorization code for access_token and refresh_token.
    Returns the full response dict from Notion, or None on failure.
    """
    auth_url = "https://api.notion.com/v1/oauth/token"
    auth_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.NOTION_REDIRECT_URI,
    }
    headers = {
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    basic_auth = aiohttp.BasicAuth(
        login=settings.NOTION_CLIENT_ID,
        password=settings.NOTION_CLIENT_SECRET,
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(auth_url, json=auth_data, headers=headers, auth=basic_auth) as resp:
            response_data = await resp.json()

            if resp.status != 200:
                logger.error(f"Notion OAuth token exchange failed: {response_data}")
                return None

            return response_data


async def refresh_access_token(user) -> Optional[str]:
    """
    Refresh an expired access token using the stored refresh_token.
    Updates the database with new tokens.
    Returns the new access_token or None on failure.
    """
    if not user.notion_refresh_token_encrypted:
        logger.error(f"No refresh token for user {user.telegram_id}")
        return None

    refresh_token = decrypt_token(user.notion_refresh_token_encrypted)
    if not refresh_token:
        return None

    headers = {
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    basic_auth = aiohttp.BasicAuth(
        login=settings.NOTION_CLIENT_ID,
        password=settings.NOTION_CLIENT_SECRET,
    )
    refresh_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.notion.com/v1/oauth/token",
            json=refresh_data,
            headers=headers,
            auth=basic_auth,
        ) as resp:
            response_data = await resp.json()

            if resp.status != 200:
                logger.error(f"Token refresh failed for user {user.telegram_id}: {response_data}")
                return None

            new_access_token = response_data.get("access_token")
            new_refresh_token = response_data.get("refresh_token")

            if new_access_token:
                update_data = {
                    "notion_access_token_encrypted": encrypt_token(new_access_token),
                }
                if new_refresh_token:
                    update_data["notion_refresh_token_encrypted"] = encrypt_token(new_refresh_token)

                await create_or_update_user(
                    telegram_id=user.telegram_id,
                    **update_data,
                )
                return new_access_token

    return None


async def discover_database_ids(access_token: str, duplicated_template_id: str) -> Optional[dict]:
    """
    Discover the database IDs from a duplicated Notion template page.
    Searches child blocks of the duplicated page for databases with known titles:
    Accounts, Expenses, Group Expenses, Categories.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": "2022-06-28",
    }

    # Database title keywords to look for (supports English template names only)
    db_mapping = {
        "Group Expenses": "group_expenses_db_id",
        "Accounts": "accounts_db_id",
        "Expenses": "expenses_db_id",
        "Categories": "categories_db_id",
    }
    result = {}

    async with aiohttp.ClientSession() as session:
        async def scan_block(block_id: str, depth: int = 0):
            if depth > 1:  # Only look 2 levels deep to avoid infinite recursion
                return
            
            logger.info(f"Scanning children of block {block_id} (depth {depth})...")
            url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to get children for {block_id}: {await resp.text()}")
                    return

                data = await resp.json()

            blocks = data.get("results", [])
            for block in blocks:
                b_type = block.get("type")
                if b_type == "child_database":
                    db_title = block.get("child_database", {}).get("title", "")
                    logger.info(f"Found database: '{db_title}' (ID: {block['id']})")
                    
                    for expected_title, field_name in db_mapping.items():
                        if expected_title.lower() in db_title.lower():
                            if field_name not in result:
                                result[field_name] = block["id"]
                                logger.info(f"MATCHED: '{db_title}' -> {field_name}")
                            break
                            
                elif b_type == "child_page":
                    page_title = block.get("child_page", {}).get("title", "")
                    logger.info(f"Found child page: '{page_title}'. Checking inside...")
                    # Recursively scan child pages (especially like "Database" page)
                    await scan_block(block["id"], depth + 1)

        # Start scanning from the root duplicated template
        await scan_block(duplicated_template_id)

    found = len(result)
    expected = 4
    if found < expected:
        logger.warning(f"Only found {found}/{expected} unique databases in template. Found fields: {list(result.keys())}")

    return result if result else None


async def search_databases_globally(access_token: str) -> Optional[Dict[str, str]]:
    """Search for databases in the entire shared workspace using Notion Search API."""
    logger.info("Starting global database search via Notion Search API...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    
    db_mapping = {
        "Group Expenses": "group_expenses_db_id",
        "Accounts": "accounts_db_id",
        "Expenses": "expenses_db_id",
        "Categories": "categories_db_id",
    }
    result = {}
    
    async with aiohttp.ClientSession() as session:
        url = "https://api.notion.com/v1/search"
        payload = {
            "filter": {"value": "database", "property": "object"},
            "page_size": 100
        }
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                logger.error(f"Global search failed: {await resp.text()}")
                return None
            data = await resp.json()

        dbs = data.get("results", [])
        logger.info(f"Search found {len(dbs)} databases in the workspace scope.")
        
        for db in dbs:
            # Extract title from title array
            title_list = db.get("title", [])
            db_title = "".join([t.get("plain_text", "") for t in title_list])
            logger.info(f"Found accessible database: '{db_title}' (ID: {db['id']})")
            
            for expected_title, field_name in db_mapping.items():
                if expected_title.lower() in db_title.lower():
                    if field_name not in result:
                        result[field_name] = db["id"]
                        logger.info(f"MATCHED (Global): '{db_title}' -> {field_name}")
                    break

    return result if result else None


async def process_oauth_callback(code: str, telegram_id: int) -> bool:
    """
    Full OAuth callback processing:
    1. Exchange code for tokens
    2. Store encrypted tokens
    3. Discover database IDs from template
    4. Update user record
    Returns True on success.
    """
    # Exchange code for tokens
    token_response = await exchange_code_for_tokens(code)
    if not token_response:
        return False

    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    duplicated_template_id = token_response.get("duplicated_template_id")
    bot_id = token_response.get("bot_id")
    workspace_id = token_response.get("workspace_id")
    workspace_name = token_response.get("workspace_name")

    if not access_token:
        logger.error("No access_token in OAuth response")
        return False

    # Prepare user update data
    update_data = {
        "notion_access_token_encrypted": encrypt_token(access_token),
        "notion_bot_id": bot_id,
        "notion_workspace_id": workspace_id,
        "notion_workspace_name": workspace_name,
    }

    if refresh_token:
        update_data["notion_refresh_token_encrypted"] = encrypt_token(refresh_token)

    # Discover database IDs
    db_ids = None
    if duplicated_template_id:
        logger.info(f"Duplicated template ID found: {duplicated_template_id}. Starting discovery...")
        db_ids = await discover_database_ids(access_token, duplicated_template_id)
    
    # Fallback to global search if no IDs found or no template ID provided
    if not db_ids:
        logger.info("Falling back to global search for databases...")
        db_ids = await search_databases_globally(access_token)

    if db_ids:
        update_data.update(db_ids)
        logger.info(f"Final discovered {len(db_ids)} databases for user {telegram_id}")
    else:
        logger.warning(f"Could not find any matching databases (tried discovery and global search) for user {telegram_id}")

    # Check if all 4 databases were found
    expected_dbs = {"accounts_db_id", "expenses_db_id", "group_expenses_db_id", "categories_db_id"}
    has_all_dbs = False
    if db_ids:
        has_all_dbs = all(key in update_data for key in expected_dbs)

    # Store everything in the database
    await create_or_update_user(telegram_id=telegram_id, **update_data)

    logger.info(f"OAuth flow completed for user {telegram_id} (workspace: {workspace_name}). Success: {True}, HasDbs: {has_all_dbs}")
    return True, has_all_dbs
