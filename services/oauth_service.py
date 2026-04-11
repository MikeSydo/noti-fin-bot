import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
from config import settings
from services.security import encrypt_token, decrypt_token
from services.user_service import create_or_update_user, get_user_by_oauth_state

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


async def get_page_title(access_token: str, page_id: str) -> Optional[str]:
    """Fetch the title of a Notion page by ID."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": "2022-06-28",
    }
    url = f"https://api.notion.com/v1/pages/{page_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                properties = data.get("properties", {})
                # For standard pages, title property is usually named "title"
                title_prop = properties.get("title") or next(iter(properties.values())) if properties else None
                if title_prop and title_prop.get("type") == "title":
                    title_list = title_prop.get("title", [])
                    return "".join([t.get("plain_text", "") for t in title_list])
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
            if depth > 3:  # Only look 4 levels deep to find nested Stats pages
                return
            
            logger.info(f"Scanning children of block {block_id} (depth {depth})...")
            url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    resp_text = await resp.text()
                    if "copy_indicator" in resp_text:
                        logger.warning(f"Skipping block {block_id} due to unsupported copy_indicator type.")
                        return
                    logger.error(f"Failed to get children for {block_id}: {resp_text}")
                    return

                data = await resp.json()

            blocks = data.get("results", [])
            for block in blocks:
                b_type = block.get("type")
                if b_type == "child_database":
                    db_title = block.get("child_database", {}).get("title", "")
                    logger.info(f"Checking database: '{db_title}' (ID: {block['id']})")
                    
                    for expected_title, field_name in db_mapping.items():
                        if expected_title.lower() in db_title.lower():
                            if field_name not in result:
                                result[field_name] = block["id"]
                                logger.info(f"MATCHED DB: '{db_title}' -> {field_name}")
                            break
                            
                elif b_type == "child_page":
                    page_title = block.get("child_page", {}).get("title", "")
                    logger.info(f"Checking child page: '{page_title}' (ID: {block['id']})")
                    
                    # Discover Stats page (flexible matching)
                    clean_title = page_title.strip().lower()
                    if clean_title == "stats" or clean_title == "statistics":
                        result["stats_page_id"] = block["id"]
                        logger.info(f"MATCHED Stats page: '{page_title}' -> stats_page_id")
                        continue

                    # Recursively scan child pages
                    try:
                        await scan_block(block["id"], depth + 1)
                    except Exception as e:
                        logger.warning(f"Could not scan inside page '{page_title}': {e}")

        # Start scanning from the root duplicated template
        await scan_block(duplicated_template_id)

    found_dbs = sum(1 for k in db_mapping.values() if k in result)
    expected_dbs = 4
    if found_dbs < expected_dbs:
        logger.warning(f"Only found {found_dbs}/{expected_dbs} unique databases in template. Found fields: {list(result.keys())}")
    
    if "stats_page_id" not in result:
        logger.warning("Stats page was not found in the template.")

    return result if result else None


async def search_notion_globally(access_token: str) -> Optional[dict[str, str]]:
    """
    Search for both databases and the Stats page in the entire shared workspace 
    using Notion Search API. Does two passes to avoid result limits.
    """
    logger.info("Starting global Notion search (2-pass)...")
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
    # results_by_parent will store: { parent_id: { field_name: db_id } }
    results_by_parent = {}
    
    async with aiohttp.ClientSession() as session:
        url = "https://api.notion.com/v1/search"
        
        # Pass 1: Search for Databases (filtered)
        logger.info("Pass 1: Searching for databases...")
        payload_db = {
            "filter": {"value": "database", "property": "object"},
            "page_size": 100
        }
        async with session.post(url, headers=headers, json=payload_db) as resp:
            if resp.status == 200:
                data = await resp.json()
                dbs = data.get("results", [])
                logger.info(f"Found {len(dbs)} databases globally.")
                for db in dbs:
                    # Get parent ID for grouping
                    parent = db.get("parent", {})
                    parent_id = parent.get("page_id") or parent.get("database_id") or "root"
                    
                    title_list = db.get("title", [])
                    title_text = "".join([t.get("plain_text", "") for t in title_list])
                    
                    for expected_title, field_name in db_mapping.items():
                        if expected_title.lower() in title_text.lower():
                            if parent_id not in results_by_parent:
                                results_by_parent[parent_id] = {}
                            
                            # Store only if not already found for THIS parent (though usually titles are unique in a page)
                            if field_name not in results_by_parent[parent_id]:
                                results_by_parent[parent_id][field_name] = db["id"]
                                logger.info(f"Matched DB (Global): '{title_text}' under {parent_id} -> {field_name}")
                            break
            else:
                logger.error(f"Global DB search failed: {await resp.text()}")

        # Pass 2: Search for Stats Page (query-augmented)
        logger.info("Pass 2: Searching for Stats page...")
        payload_page = {
            "query": "Stats",
            "filter": {"value": "page", "property": "object"},
            "page_size": 20
        }
        async with session.post(url, headers=headers, json=payload_page) as resp:
            if resp.status == 200:
                data = await resp.json()
                pages = data.get("results", [])
                logger.info(f"Found {len(pages)} pages globally matching 'Stats'.")
                for page in pages:
                    # Get parent ID for grouping
                    parent = page.get("parent", {})
                    parent_id = parent.get("page_id") or parent.get("database_id") or "root"
                    
                    properties = page.get("properties", {})
                    title_text = ""
                    for prop in properties.values():
                        if prop.get("type") == "title":
                            title_list = prop.get("title", [])
                            title_text = "".join([t.get("plain_text", "") for t in title_list])
                            break
                    
                    if not title_text:
                        continue
                        
                    clean_title = title_text.strip().lower()
                    if "stats" in clean_title or "statistics" in clean_title:
                        if parent_id not in results_by_parent:
                            results_by_parent[parent_id] = {}
                            
                        if "stats_page_id" not in results_by_parent[parent_id]:
                            results_by_parent[parent_id]["stats_page_id"] = page["id"]
                            logger.info(f"Matched Stats page (Global): '{title_text}' under {parent_id} -> stats_page_id")
            else:
                logger.error(f"Global Page search failed: {await resp.text()}")

    if not results_by_parent:
        return None

    # Pick the "best" parent: the one that has the most matching fields
    best_parent_id = max(results_by_parent, key=lambda p_id: len(results_by_parent[p_id]))
    result = results_by_parent[best_parent_id]
    
    logger.info(f"Selected parent '{best_parent_id}' with {len(result)} matching items as the best candidate.")
    return result


async def process_oauth_callback(code: str, telegram_id: int) -> tuple[bool, dict]:
    """
    Step 1 of OAuth callback processing:
    1. Exchange code for tokens
    2. Return token info and success status
    """
    token_response = await exchange_code_for_tokens(code)
    if not token_response:
        return False, {}

    access_token = token_response.get("access_token")
    if not access_token:
        logger.error("No access_token in OAuth response")
        return False, {}

    return True, token_response


async def complete_oauth_discovery(token_response: dict, telegram_id: int):
    """
    Step 2 of OAuth callback processing (Run in background):
    1. Store encrypted tokens
    2. Discover database IDs
    3. Update user record
    4. Notify user via Telegram
    """
    from bot import bot
    from services.i18n import i18n
    from app.keyboards.reply import get_main_menu

    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    duplicated_template_id = token_response.get("duplicated_template_id")
    bot_id = token_response.get("bot_id")
    workspace_id = token_response.get("workspace_id")
    workspace_name = token_response.get("workspace_name")

    # Prepare user update data
    update_data = {
        "notion_access_token_encrypted": encrypt_token(access_token),
        "notion_bot_id": bot_id,
        "notion_workspace_id": workspace_id,
        "notion_workspace_name": workspace_name,
        "notion_template_name": "Finance Tracker",  # Default fallback
    }

    # Fetch real template name if available
    if duplicated_template_id:
        template_name = await get_page_title(access_token, duplicated_template_id)
        if template_name:
            update_data["notion_template_name"] = template_name

    if refresh_token:
        update_data["notion_refresh_token_encrypted"] = encrypt_token(refresh_token)

    # Discover database IDs from template
    db_ids = {}
    if duplicated_template_id:
        logger.info(f"Duplicated template ID found: {duplicated_template_id} for user {telegram_id}. Starting discovery...")
        db_ids = await discover_database_ids(access_token, duplicated_template_id) or {}
    
    # Check if we are missing anything
    required_ids = {"accounts_db_id", "expenses_db_id", "group_expenses_db_id", "categories_db_id", "stats_page_id"}
    missing_ids = [k for k in required_ids if k not in db_ids]
    
    # Fallback to global search if anything is missing
    if missing_ids:
        logger.info(f"Missing {missing_ids} for user {telegram_id}. Falling back to global search...")
        global_ids = await search_notion_globally(access_token)
        if global_ids:
            # We found a better candidate globally. 
            # To ensure consistency, we don't just merge; we should ideally 
            # re-run discovery from the common parent if possible.
            # However, search_notion_globally already returns a consistent set 
            # from the 'best' parent it found.
            
            # If the global search found MORE than we have, or different ones, 
            # let's trust its grouping.
            if len(global_ids) > len(db_ids):
                logger.info(f"Global search found a more complete project ({len(global_ids)} items). Switching to it.")
                db_ids = global_ids
            else:
                # Merge only if it doesn't break consistency (heuristic: only if db_ids was empty)
                for k, v in global_ids.items():
                    if k not in db_ids:
                        db_ids[k] = v
            logger.info(f"Global search results processed. Current found count: {len(db_ids)}")

    if db_ids:
        update_data.update(db_ids)
        logger.info(f"Final discovered {len(db_ids)} objects for user {telegram_id}")
    else:
        logger.warning(f"Could not find any matching objects (tried discovery and global search) for user {telegram_id}")

    # Check if all 4 databases were found
    expected_dbs = {"accounts_db_id", "expenses_db_id", "group_expenses_db_id", "categories_db_id"}
    has_all_dbs = False
    if db_ids:
        has_all_dbs = all(key in update_data for key in expected_dbs)

    # Store everything in the database
    await create_or_update_user(telegram_id=telegram_id, **update_data)
    logger.info(f"OAuth background discovery completed for user {telegram_id} (workspace: {workspace_name}). HasDbs: {has_all_dbs}")

    # Notify user in Telegram
    try:
        if has_all_dbs:
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
        logger.error(f"Failed to send background success message to {telegram_id}: {e}")
