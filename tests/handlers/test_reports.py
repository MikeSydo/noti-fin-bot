import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.handlers.reports import start_report

@pytest.mark.asyncio
async def test_start_analytics_sends_link():
    """
    Verifies that the analytics handler sends a message with an Inline URL button.
    """
    # 1. Setup mocks
    message = AsyncMock()
    message.from_user.id = 12345
    
    state = AsyncMock()
    
    user = MagicMock()
    user.stats_page_id = "abc-123-def-456"
    
    # 2. Call handler
    await start_report(message, state, user)
    
    # 3. Assertions
    # Ensure message.answer was called
    message.answer.assert_called_once()
    
    # Ensure it contains a keyboard with a URL button
    args, kwargs = message.answer.call_args
    keyboard = kwargs.get("reply_markup")
    assert keyboard is not None
    
    button = keyboard.inline_keyboard[0][0]
    assert button.url == "https://www.notion.so/abc123def456"
