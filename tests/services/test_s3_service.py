import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@pytest.mark.asyncio
@patch('services.s3_service.s3_client')
async def test_upload_receipt_to_s3_success(mock_s3):
    """Test that upload_receipt_to_s3 returns a valid URL on success."""
    mock_s3.upload_fileobj = MagicMock(return_value=None)

    import config
    config.settings.AWS_S3_BUCKET_NAME = "test-bucket"
    config.settings.AWS_REGION = "us-east-1"

    from services.s3_service import upload_receipt_to_s3
    result = await upload_receipt_to_s3(b"fake_image_bytes", file_extension="jpg")

    assert result is not None
    assert result.startswith("https://test-bucket.s3.us-east-1.amazonaws.com/receipts/")
    assert result.endswith(".jpg")
    mock_s3.upload_fileobj.assert_called_once()


@pytest.mark.asyncio
@patch('services.s3_service.s3_client')
async def test_upload_receipt_to_s3_client_error(mock_s3):
    """Test that upload_receipt_to_s3 returns None on ClientError."""
    from botocore.exceptions import ClientError
    mock_s3.upload_fileobj = MagicMock(
        side_effect=ClientError(
            {'Error': {'Code': '403', 'Message': 'Forbidden'}},
            'upload_fileobj'
        )
    )

    from services.s3_service import upload_receipt_to_s3
    result = await upload_receipt_to_s3(b"fake_image_bytes", file_extension="jpg")

    assert result is None


@pytest.mark.asyncio
@patch('services.s3_service.s3_client')
async def test_upload_receipt_to_s3_generic_error(mock_s3):
    """Test that upload_receipt_to_s3 returns None on unexpected exceptions."""
    mock_s3.upload_fileobj = MagicMock(side_effect=Exception("Unexpected error"))

    from services.s3_service import upload_receipt_to_s3
    result = await upload_receipt_to_s3(b"fake_image_bytes", file_extension="png")

    assert result is None


@pytest.mark.asyncio
@patch('services.s3_service.s3_client')
async def test_upload_receipt_to_s3_unique_filenames(mock_s3):
    """Test that each upload generates a unique file path."""
    mock_s3.upload_fileobj = MagicMock(return_value=None)

    from services.s3_service import upload_receipt_to_s3
    result1 = await upload_receipt_to_s3(b"bytes1")
    result2 = await upload_receipt_to_s3(b"bytes2")

    assert result1 != result2
