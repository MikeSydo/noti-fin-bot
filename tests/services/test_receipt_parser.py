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
    assert isinstance(result, ParsedReceipt)
    assert result.is_receipt is True
    assert result.store_name == "METRO"
    assert result.total_amount == 506.06
    assert result.date == "28-03-2026"
    assert len(result.items) == 2

    # Verify the REAL image bytes were passed to Gemini
    mock_genai_client.aio.models.generate_content.assert_called_once()
    _args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert kwargs["contents"][1].inline_data.data == mock_receipt_bytes


@pytest.mark.asyncio
async def test_parse_receipt_not_receipt(mock_genai_client, mock_receipt_bytes):
    """Test that is_receipt=False is correctly returned when Gemini says no."""
    mock_response = MagicMock()
    mock_data = {
        "is_receipt": False,
        "store_name": "",
        "group_expense_name": "",
        "total_amount": 0.0,
        "date": "",
        "items": []
    }
    mock_response.text = json.dumps(mock_data)

    async def mock_generate(*args, **kwargs):
        return mock_response

    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    result = await parse_receipt(mock_receipt_bytes, [], lang_code="uk")

    assert result is not None
    assert result.is_receipt is False


@pytest.mark.asyncio
async def test_parse_receipt_empty_response(mock_genai_client):
    """Test that parse_receipt returns None on empty Gemini response."""
    mock_response = MagicMock()
    mock_response.text = ""

    async def mock_generate(*args, **kwargs):
        return mock_response

    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    result = await parse_receipt(b"fake_image_bytes", ["Food"])

    assert result is None


@pytest.mark.asyncio
async def test_parse_receipt_exception(mock_genai_client):
    """Test that parse_receipt returns None when Gemini raises an exception."""
    async def mock_generate(*args, **kwargs):
        raise Exception("API Error")

    mock_genai_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

    result = await parse_receipt(b"fake_image_bytes", ["Food"])

    assert result is None
