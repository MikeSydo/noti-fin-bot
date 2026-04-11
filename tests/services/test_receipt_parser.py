import pytest
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from services.receipt_parser import parse_receipt

# Path to real mock receipt images - use absolute path to be more robust in CI
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOCK_JPG_PATH = os.path.join(BASE_DIR, "mock_files/Receipt_jpg.jpg")
MOCK_PNG_PATH = os.path.join(BASE_DIR, "mock_files/Receipt_png.png")
MOCK_PDF_PATH = os.path.join(BASE_DIR, "mock_files/Receipt_pdf.pdf")


@pytest.fixture
def mock_jpg_bytes() -> bytes:
    """Load real JPG receipt image bytes."""
    if not os.path.exists(MOCK_JPG_PATH):
        raise FileNotFoundError(f"Mock receipt file not found at: {MOCK_JPG_PATH}")
    with open(MOCK_JPG_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def mock_png_bytes() -> bytes:
    """Load real PNG receipt image bytes."""
    if not os.path.exists(MOCK_PNG_PATH):
        raise FileNotFoundError(f"Mock receipt file not found at: {MOCK_PNG_PATH}")
    with open(MOCK_PNG_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def mock_pdf_bytes() -> bytes:
    """Load real PDF receipt bytes."""
    if not os.path.exists(MOCK_PDF_PATH):
        raise FileNotFoundError(f"Mock receipt file not found at: {MOCK_PDF_PATH}")
    with open(MOCK_PDF_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def mock_genai_client():
    with patch("services.receipt_parser.client") as MockClient:
        yield MockClient


@pytest.mark.asyncio
async def test_parse_receipt_jpg_success(mock_genai_client, mock_jpg_bytes):
    """Test that a real JPG receipt image is correctly parsed (Gemini is mocked)."""
    mock_response = MagicMock()
    mock_data = {
        "is_receipt": True,
        "store_name": "METRO",
        "group_expense_name": "Продукти в METRO",
        "total_amount": 506.06,
        "date": "28-03-2026",
        "items": [
            {"name": "LOVITA ПЕЧ ФУНДУК 127Г", "amount": 64.74, "category_name": "Продукти"},
        ]
    }
    mock_response.text = json.dumps(mock_data)
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await parse_receipt(mock_jpg_bytes, ["Продукти"], lang_code="uk", mime_type="image/jpeg")

    assert result is not None
    assert result.is_receipt is True
    assert result.store_name == "METRO"
    mock_genai_client.aio.models.generate_content.assert_called_once()
    _args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert kwargs["contents"][1].inline_data.mime_type == "image/jpeg"


@pytest.mark.asyncio
async def test_parse_receipt_png_success(mock_genai_client, mock_png_bytes):
    """Test that a real PNG receipt image is correctly parsed."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({"is_receipt": True, "store_name": "Apple", "total_amount": 9.99, "items": [], "group_expense_name": "Test", "date": "01-01-2026"})
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await parse_receipt(mock_png_bytes, [], lang_code="en", mime_type="image/png")

    assert result is not None
    assert result.is_receipt is True
    _args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert kwargs["contents"][1].inline_data.mime_type == "image/png"


@pytest.mark.asyncio
async def test_parse_receipt_pdf_success(mock_genai_client, mock_pdf_bytes):
    """Test that a real PDF receipt is correctly parsed."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({"is_receipt": True, "store_name": "Google", "total_amount": 1.99, "items": [], "group_expense_name": "Test", "date": "01-01-2026"})
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await parse_receipt(mock_pdf_bytes, [], lang_code="en", mime_type="application/pdf")

    assert result is not None
    assert result.is_receipt is True
    _args, kwargs = mock_genai_client.aio.models.generate_content.call_args
    assert kwargs["contents"][1].inline_data.mime_type == "application/pdf"


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
