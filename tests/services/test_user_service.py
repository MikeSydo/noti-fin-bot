import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.user import User


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_get_user_found(mock_session_factory):
    """Test that get_user returns a User when found."""
    mock_user = User(telegram_id=123456, username="testuser", language="en")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import get_user
    user = await get_user(123456)

    assert user is not None
    assert user.telegram_id == 123456
    assert user.username == "testuser"


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_get_user_not_found(mock_session_factory):
    """Test that get_user returns None when user doesn't exist."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import get_user
    user = await get_user(999999)

    assert user is None


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_get_user_by_oauth_state_found(mock_session_factory):
    """Test that get_user_by_oauth_state returns a User with matching state."""
    mock_user = User(telegram_id=111, oauth_state="valid_state_token")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import get_user_by_oauth_state
    user = await get_user_by_oauth_state("valid_state_token")

    assert user is not None
    assert user.telegram_id == 111


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_get_user_by_oauth_state_not_found(mock_session_factory):
    """Test that get_user_by_oauth_state returns None when state not found."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import get_user_by_oauth_state
    user = await get_user_by_oauth_state("nonexistent_state")

    assert user is None


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_create_or_update_user_creates_new(mock_session_factory):
    """Test that create_or_update_user creates a new user if not found."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # User doesn't exist
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import create_or_update_user
    user = await create_or_update_user(999, username="newuser", language="uk")

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_create_or_update_user_updates_existing(mock_session_factory):
    """Test that create_or_update_user updates existing user fields."""
    existing_user = User(telegram_id=123, username="oldname", language="en")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import create_or_update_user
    await create_or_update_user(123, username="newname", language="uk")

    assert existing_user.username == "newname"
    assert existing_user.language == "uk"
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_clear_user_notion_data_success(mock_session_factory):
    """Test that clear_user_notion_data clears all Notion fields."""
    user = User(
        telegram_id=123,
        notion_access_token_encrypted=b"token",
        accounts_db_id="acc_db",
        expenses_db_id="exp_db",
        group_expenses_db_id="grexp_db",
        categories_db_id="cat_db",
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import clear_user_notion_data
    result = await clear_user_notion_data(123)

    assert result is True
    assert user.notion_access_token_encrypted is None
    assert user.accounts_db_id is None
    assert user.expenses_db_id is None
    assert user.group_expenses_db_id is None
    assert user.categories_db_id is None


@pytest.mark.asyncio
@patch('services.user_service.AsyncSessionLocal')
async def test_clear_user_notion_data_user_not_found(mock_session_factory):
    """Test that clear_user_notion_data returns False if user not found."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = mock_session

    from services.user_service import clear_user_notion_data
    result = await clear_user_notion_data(999)

    assert result is False


@pytest.mark.asyncio
@patch('services.user_service.get_user', new_callable=AsyncMock)
async def test_get_user_language_found(mock_get_user):
    """Test that get_user_language returns user's language code."""
    mock_get_user.return_value = User(telegram_id=1, language="uk")

    from services.user_service import get_user_language
    lang = await get_user_language(1)

    assert lang == "uk"


@pytest.mark.asyncio
@patch('services.user_service.get_user', new_callable=AsyncMock)
async def test_get_user_language_not_found_defaults_to_uk(mock_get_user):
    """Test that get_user_language defaults to 'uk' when user not found."""
    mock_get_user.return_value = None

    from services.user_service import get_user_language
    lang = await get_user_language(999)

    assert lang == "uk"
