import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.oauth_service import search_notion_globally

@pytest.mark.asyncio
@patch('aiohttp.ClientSession.post')
async def test_search_notion_globally_mixed_setup_bug(mock_post):
    """
    Demonstrates the bug: search_notion_globally picks the first found item 
    for each category, regardless of their parent page, which can lead 
    to a mixed setup.
    """
    # Mocking Search API response with mixed parents
    # Page A (Incomplete)
    # Page B (Complete)
    
    mock_resp_db = MagicMock()
    mock_resp_db.status = 200
    mock_resp_db.json = AsyncMock(return_value={
        "results": [
            # 1. Expenses from Page A (comes first)
            {
                "object": "database", 
                "id": "db_exp_A", 
                "title": [{"plain_text": "Expenses"}],
                "parent": {"type": "page_id", "page_id": "page_A"}
            },
            # 2. Accounts from Page B (comes next)
            {
                "object": "database", 
                "id": "db_acc_B", 
                "title": [{"plain_text": "Accounts"}],
                "parent": {"type": "page_id", "page_id": "page_B"}
            },
            # 3. Expenses from Page B (later)
            {
                "object": "database", 
                "id": "db_exp_B", 
                "title": [{"plain_text": "Expenses"}],
                "parent": {"type": "page_id", "page_id": "page_B"}
            },
            # 4. Accounts from Page A (later)
            {
                "object": "database", 
                "id": "db_acc_A", 
                "title": [{"plain_text": "Accounts"}],
                "parent": {"type": "page_id", "page_id": "page_A"}
            },
        ]
    })
    
    # Second pass: Stats Page (also from Page B)
    mock_resp_page = MagicMock()
    mock_resp_page.status = 200
    mock_resp_page.json = AsyncMock(return_value={
        "results": [
            {
                "object": "page", 
                "id": "page_stats_B", 
                "parent": {"type": "page_id", "page_id": "page_B"},
                "properties": {
                    "title": {"type": "title", "title": [{"plain_text": "Stats"}]}
                }
            }
        ]
    })
    
    mock_post.side_effect = [
        MagicMock(__aenter__=AsyncMock(return_value=mock_resp_db)),
        MagicMock(__aenter__=AsyncMock(return_value=mock_resp_page))
    ]
    
    # Current behavior will likely return MIXED: db_exp_A and db_acc_B
    result = await search_notion_globally("fake_token")
    
    # After fix, it should return consistent IDs from the most complete parent (Page B)
    assert result["expenses_db_id"] == "db_exp_B"
    assert result["accounts_db_id"] == "db_acc_B"
    assert result["stats_page_id"] == "page_stats_B"
