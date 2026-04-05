import logging
from typing import Optional
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models.user import User

logger = logging.getLogger(__name__)


async def get_user(telegram_id: int) -> Optional[User]:
    """Retrieve user from the database by Telegram ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_by_oauth_state(state: str) -> Optional[User]:
    """Retrieve user by OAuth CSRF state token."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.oauth_state == state))
        return result.scalar_one_or_none()


async def create_or_update_user(telegram_id: int, username: str = None, **kwargs) -> User:
    """Create a new user or update an existing one."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(telegram_id=telegram_id, username=username, **kwargs)
            session.add(user)
        else:
            if username is not None:
                user.username = username
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

        await session.commit()
        await session.refresh(user)
        return user


async def clear_user_notion_data(telegram_id: int) -> bool:
    """Clear all Notion-related data for a user (disconnect)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.notion_access_token_encrypted = None
        user.notion_refresh_token_encrypted = None
        user.notion_bot_id = None
        user.notion_workspace_id = None
        user.notion_workspace_name = None
        user.accounts_db_id = None
        user.expenses_db_id = None
        user.group_expenses_db_id = None
        user.categories_db_id = None

        await session.commit()
        return True


async def get_user_language(telegram_id: int) -> str:
    """Get the user's language, default to 'uk'."""
    user = await get_user(telegram_id)
    return user.language if user and user.language else "uk"


async def set_user_language(telegram_id: int, language_code: str):
    """Set the user's language."""
    await create_or_update_user(telegram_id, language=language_code)
