import io
import uuid
import boto3
from botocore.exceptions import ClientError
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize boto3 client
s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

async def upload_receipt_to_s3(file_bytes: bytes, file_extension: str = "jpg") -> str | None:
    """
    Uploads a file to AWS S3 and returns the public URL.
    Runs synchronously but wrapped in asyncio.to_thread for aiogram compatibility.
    """
    file_name = f"receipts/{uuid.uuid4().hex}.{file_extension}"
    
    def _upload():
        try:
            # Map extensions to standard MIME types
            mime_types = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "pdf": "application/pdf"
            }
            content_type = mime_types.get(file_extension.lower(), f"image/{file_extension}")

            s3_client.upload_fileobj(
                io.BytesIO(file_bytes),
                settings.AWS_S3_BUCKET_NAME,
                file_name,
                ExtraArgs={
                    "ContentType": content_type
                }
            )
            # Generate the reliable standard URL (since bucket is public)
            url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
            return url
        except ClientError as e:
            logger.error(f"AWS S3 Upload Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected S3 Upload Error: {e}")
            return None

    return await asyncio.to_thread(_upload)
