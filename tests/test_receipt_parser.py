import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from services.receipt_parser import parse_receipt, ParsedReceipt

@pytest.fixture
def mock_genai_client():
    with patch("services.receipt_parser.client") as MockClient:
        yield MockClient

@pytest.mark.asyncio
async def test_parse_receipt_success(mock_genai_client):
    # Setup mock response
    mock_response = MagicMock()
    
    mock_data = {
        "store_name": "Test Store",
        "group_expense_name": "Groceries in Test Store",
        "total_amount": 100.50,
        "date": "2023-10-27",
        "items": [
            {"name": "Milk", "amount": 50.25, "category_name": "Food"},
            {"name": "Bread", "amount": 50.25, "category_name": "Food"}
        ]
    }
    
    mock_response.text = json.dumps(mock_data)
    
    async def mock_generate(*args, **kwargs):
        return mock_response
        
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    # Call the function
    result = await parse_receipt(b"fake_image_bytes", ["Food", "Transport"])

    # Assertions
    assert result is not None
    assert isinstance(result, ParsedReceipt)
    assert result.store_name == "Test Store"
    assert result.group_expense_name == "Groceries in Test Store"
    assert result.total_amount == 100.50
    assert result.date == "2023-10-27"
    assert len(result.items) == 2
    assert result.items[0].name == "Milk"
    assert result.items[0].amount == 50.25
    assert result.items[0].category_name == "Food"

    # Verify model was called correctly
    mock_genai_client.aio.models.generate_content.assert_called_once()
    args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert b"fake_image_bytes" == kwargs["contents"][1].inline_data.data


@pytest.mark.asyncio
async def test_parse_receipt_empty_response(mock_genai_client):
    # Setup mock response with empty text
    mock_response = MagicMock()
    mock_response.text = ""
    
    async def mock_generate(*args, **kwargs):
        return mock_response
        
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    # Call the function
    result = await parse_receipt(b"fake_image_bytes", ["Food"])

    # Assertions
    assert result is None

@pytest.mark.asyncio
async def test_parse_receipt_exception(mock_genai_client):
    # Setup mock to raise exception
    async def mock_generate(*args, **kwargs):
        raise Exception("API Error")
        
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    # Call the function
    result = await parse_receipt(b"fake_image_bytes", ["Food"])

    # Assertions
    assert result is None

