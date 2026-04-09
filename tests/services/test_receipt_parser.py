import pytest
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from services.receipt_parser import parse_receipt, ParsedReceipt

# Path to real mock receipt image
MOCK_RECEIPT_PATH = os.path.join(os.path.dirname(__file__), "../../mock_files/file_9.jpg")


@pytest.fixture
def mock_receipt_bytes() -> bytes:
    """Load real receipt image bytes from mock_files."""
    with open(MOCK_RECEIPT_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def mock_genai_client():
    with patch("services.receipt_parser.client") as MockClient:
        yield MockClient


@pytest.mark.asyncio
async def test_parse_receipt_success(mock_genai_client, mock_receipt_bytes):
    """Test that a real receipt image is correctly parsed (Gemini is mocked)."""
    mock_response = MagicMock()

    mock_data = {
        "is_receipt": True,
        "store_name": "METRO",
        "group_expense_name": "Продукти в METRO",
        "total_amount": 506.06,
        "date": "28-03-2026",
        "items": [
            {"name": "LOVITA ПЕЧ ФУНДУК 127Г", "amount": 64.74, "category_name": "Продукти"},
            {"name": "LMR ГЕЛЬ Д/ДУШУ 250МЛ АРГАН", "amount": 50.83, "category_name": "Побутова хімія"},
        ]
    }

    mock_response.text = json.dumps(mock_data)

    async def mock_generate(*args, **kwargs):
        return mock_response

    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    # Call with real image bytes and image/jpeg mime type
    result = await parse_receipt(mock_receipt_bytes, ["Продукти", "Побутова хімія"], lang_code="uk", mime_type="image/jpeg")

    # Assertions
    assert result is not None
    assert result.store_name == "METRO"
    
    # Verify the CORRECT model is used (Gemini 2.5 Flash as requested)
    mock_genai_client.aio.models.generate_content.assert_called_once()
    _args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_parse_receipt_retry_logic(mock_genai_client):
    """Test that parse_receipt retries on 503 errors and eventually succeeds."""
    mock_response = MagicMock()
    mock_data = {"is_receipt": False, "store_name": "", "group_expense_name": "", "total_amount": 0.0, "date": "", "items": []}
    mock_response.text = json.dumps(mock_data)

    # First and second calls raise 503, third call succeeds
    side_effects = [
        Exception("503 Service Unavailable"),
        Exception("503 Service Unavailable"),
        mock_response
    ]
    
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=side_effects)

    # Use small delay to speed up tests
    with patch("asyncio.sleep", return_value=None):
        result = await parse_receipt(b"fake_bytes", [])

    assert result is not None
    assert mock_genai_client.aio.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_parse_receipt_empty_response_raises(mock_genai_client):
    """Test that parse_receipt RAISES an exception on empty Gemini response after retries."""
    mock_response = MagicMock()
    mock_response.text = ""

    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("asyncio.sleep", return_value=None):
        with pytest.raises(Exception, match="Empty response from Gemini API"):
            await parse_receipt(b"fake_image_bytes", ["Food"])


@pytest.mark.asyncio
async def test_parse_receipt_exception_re_raised(mock_genai_client):
    """Test that parse_receipt re-raises the exception after retries if it's not a temporary error."""
    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=Exception("Permanent API Error"))

    with pytest.raises(Exception, match="Permanent API Error"):
        await parse_receipt(b"fake_image_bytes", ["Food"])
