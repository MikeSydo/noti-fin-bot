import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.handlers.group_expenses import process_expense_toggle

@pytest.mark.asyncio
async def test_process_expense_toggle_maintains_page():
    """
    TDD Test: Verifies that toggling an expense maintains the current pagination page.
    Currently, the code is bugged and resets to page 0.
    """
    # 1. Setup mocks
    callback = AsyncMock()
    # Mock callback data to include a page (simulating our future fix)
    callback.data = "toggle_grexpense_rel_expense123:1" 
    callback.from_user.id = 12345
    callback.message = AsyncMock()
    
    state = AsyncMock()
    state.get_data.return_value = {"selected_expenses_ids": []}
    
    notion_writer = AsyncMock()
    # Mock get_expenses_list to return some dummy data
    notion_writer.get_expenses_list.return_value = [MagicMock(id=f"exp_{i}") for i in range(10)]
    
    # 2. Call the handler
    # Note: We expect this to FAIL to maintain page 1 before the fix
    # because it currently ignores the page part of the callback 
    # and hardcodes page=0.
    
    with patch("app.handlers.group_expenses.show_expenses_selection", new_callable=AsyncMock) as mock_show:
        await process_expense_toggle(callback, state, notion_writer)
        
        # 3. Assertions
        # If the bug is present, mock_show will be called with page=0
        # If fixed, it should be called with page=1
        args, kwargs = mock_show.call_args
        assert kwargs.get("page") == 1, f"Expected page 1, but got {kwargs.get('page')}"
