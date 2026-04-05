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
