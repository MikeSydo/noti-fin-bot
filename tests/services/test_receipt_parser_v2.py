import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from services.receipt_parser import parse_receipt

@pytest.fixture
def mock_genai_client():
    with patch("services.receipt_parser.client") as MockClient:
        yield MockClient

@pytest.mark.asyncio
async def test_parse_receipt_with_confidence_high(mock_genai_client):
    """Test that a receipt with high confidence is correctly parsed."""
    mock_response = MagicMock()
    mock_data = {
        "is_receipt": True,
        "store_name": "Walmart",
        "group_expense_name": "Groceries at Walmart",
        "total_amount": 100.0,
        "date": "11-04-2026",
        "items": [{"name": "Milk", "amount": 100.0, "category_name": "Food", "is_uncertain": False}],
        "confidence_score": 100,
        "currency_hint": "USD",
        "uncertain_fields": []
    }
    mock_response.text = json.dumps(mock_data)
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await parse_receipt(b"fake_bytes", ["Food"], lang_code="en")

    assert result is not None
    assert result.confidence_score == 100
    assert result.currency_hint == "USD"
    assert result.uncertain_fields == []
    assert result.items[0].is_uncertain is False

@pytest.mark.asyncio
async def test_parse_receipt_with_discounts(mock_genai_client):
    """Test that discounts (negative amounts) are handled."""
    mock_response = MagicMock()
    mock_data = {
        "is_receipt": True,
        "store_name": "Silpo",
        "group_expense_name": "Продукти в Сільпо",
        "total_amount": 80.0,
        "date": "11-04-2026",
        "items": [
            {"name": "Cheese", "amount": 100.0, "category_name": "Food", "is_uncertain": False},
            {"name": "Discount", "amount": -20.0, "category_name": "Discounts", "is_uncertain": False}
        ],
        "confidence_score": 95,
        "currency_hint": "UAH",
        "uncertain_fields": []
    }
    mock_response.text = json.dumps(mock_data)
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await parse_receipt(b"fake_bytes", ["Food", "Discounts"], lang_code="uk")

    assert result is not None
    assert len(result.items) == 2
    assert result.items[1].amount == -20.0
    assert result.total_amount == 80.0
