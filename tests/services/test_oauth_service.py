import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.oauth_service import generate_oauth_url, validate_oauth_state
from models.user import User
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
@patch('services.oauth_service.create_or_update_user', new_callable=AsyncMock)
async def test_generate_oauth_url(mock_create_user):
    import config
    # Set dummy configs just for this test
    original_client_id = config.settings.NOTION_CLIENT_ID
    original_redirect_uri = config.settings.NOTION_REDIRECT_URI
    config.settings.NOTION_CLIENT_ID = "test_client_id"
    config.settings.NOTION_REDIRECT_URI = "http://localhost/callback"
    
    url = await generate_oauth_url(12345)
    
    assert "https://api.notion.com/v1/oauth/authorize" in url
    assert "client_id=test_client_id" in url
    assert "redirect_uri=http://localhost/callback" in url
    assert "state=" in url
    
    mock_create_user.assert_called_once()
    kwargs = mock_create_user.call_args.kwargs
    assert kwargs["telegram_id"] == 12345
    assert "oauth_state" in kwargs
    assert "oauth_state_expires" in kwargs
    
    config.settings.NOTION_CLIENT_ID = original_client_id
    config.settings.NOTION_REDIRECT_URI = original_redirect_uri


@pytest.mark.asyncio
@patch('services.oauth_service.get_user_by_oauth_state', new_callable=AsyncMock)
@patch('services.oauth_service.create_or_update_user', new_callable=AsyncMock)
async def test_validate_oauth_state_success(mock_update, mock_get_user):
    fake_user = User(
        telegram_id=12345,
        oauth_state="valid_state",
        oauth_state_expires=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    mock_get_user.return_value = fake_user
    
    result = await validate_oauth_state("valid_state")
    
    assert result == 12345
    mock_update.assert_called_once_with(
        telegram_id=12345,
        oauth_state=None,
        oauth_state_expires=None
    )


@pytest.mark.asyncio
@patch('services.oauth_service.get_user_by_oauth_state', new_callable=AsyncMock)
async def test_validate_oauth_state_not_found(mock_get_user):
    mock_get_user.return_value = None
    
    result = await validate_oauth_state("invalid_state")
    assert result is None


@pytest.mark.asyncio
@patch('services.oauth_service.get_user_by_oauth_state', new_callable=AsyncMock)
@patch('services.oauth_service.create_or_update_user', new_callable=AsyncMock)
async def test_validate_oauth_state_expired(mock_update, mock_get_user):
    fake_user = User(
        telegram_id=12345,
        oauth_state="expired_state",
        oauth_state_expires=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    mock_get_user.return_value = fake_user
    
    result = await validate_oauth_state("expired_state")
    
    assert result is None
    mock_update.assert_called_once_with(
        telegram_id=12345,
        oauth_state=None,
        oauth_state_expires=None
    )


@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_discover_database_ids_success_en(mock_get):
    """Test that English database names are correctly matched."""
    from services.oauth_service import discover_database_ids
    
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={
        "results": [
            {"type": "child_database", "id": "db_1", "child_database": {"title": "Expenses"}},
            {"type": "child_database", "id": "db_2", "child_database": {"title": "Accounts"}},
            {"type": "child_database", "id": "db_3", "child_database": {"title": "Categories"}},
            {"type": "child_database", "id": "db_4", "child_database": {"title": "Group Expenses"}},
        ]
    })
    mock_get.return_value.__aenter__.return_value = mock_resp
    
    result = await discover_database_ids("fake_token", "template_id")
    
    assert result["expenses_db_id"] == "db_1"
    assert result["accounts_db_id"] == "db_2"
    assert result["categories_db_id"] == "db_3"
    assert result["group_expenses_db_id"] == "db_4"


@pytest.mark.asyncio
@patch('aiohttp.ClientSession.get')
async def test_discover_database_ids_copy_indicator_skip(mock_get):
    """Test that copy_indicator error is caught and does not crash the process."""
    from services.oauth_service import discover_database_ids
    
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_resp.text = AsyncMock(return_value='{"message": "Block type copy_indicator is not supported via the API."}')
    mock_get.return_value.__aenter__.return_value = mock_resp
    
    # Should not raise exception, but return what it found (None since nothing matched)
    result = await discover_database_ids("fake_token", "template_id")
    assert result is None
