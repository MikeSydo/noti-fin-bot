import json
import logging
import asyncio
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class ParsedItem(BaseModel):
    name: str = Field(description="Name of the item")
    amount: float = Field(description="Price/Amount of the item")
    category_name: Optional[str] = Field(description="Best fitting category name from the provided list, or None")

class ParsedReceipt(BaseModel):
    is_receipt: bool = Field(description="Set to true ONLY if the image is a receipt. Set to false if it's a person, landscape, or anything else.")
    store_name: str = Field(description="Name of the store or place. Empty if not a receipt.")
    group_expense_name: str = Field(description="A descriptive name for the entire receipt, formatted like '[Theme] in [Store name]'. E.g. 'Продукти в Сільпо' or 'Groceries at Walmart'. Use the language of the receipt. Empty if not a receipt.")
    total_amount: float = Field(description="Total amount of the receipt. 0 if not a receipt.")
    date: str = Field(description="Date of the receipt in DD-MM-YYYY format. Empty if not a receipt.")
    items: List[ParsedItem] = Field(description="List of purchased items")

async def parse_receipt(file_bytes: bytes, categories: List[str], lang_code: str = "uk", mime_type: str = "image/jpeg") -> Optional[ParsedReceipt]:
    """
    Parses a receipt image using Gemini and extracts structured data.
    Includes retry logic for 503/504 service errors.
    """
    max_retries = 3
    retry_delay = 2 # seconds

    for attempt in range(max_retries):
        try:
            lang_name = "Ukrainian" if lang_code == "uk" else "English"
            prompt = f"""
            Analyze this image. Your first task is to determine if it is a receipt.
            A receipt is a document issued by a store, restaurant, or service provider showing proof of purchase. It often contains a store name, a list of items, and a total amount. It MAY be a photo of a paper receipt, potentially taken at an angle, in low light, or against various backgrounds.
            
            If it's NOT a receipt (e.g., a photo of a person, animal, nature, or a random object with no text), set "is_receipt" to false and leave other fields empty.
            
            If it IS a receipt, extract the following information:
            - Store name (store_name)
            - A general name for the whole receipt (group_expense_name) such as "Продукти в Сільпо" or "Electronics in BestBuy".
            - Total amount (total_amount)
            - Date in DD-MM-YYYY format (date)
            - A list of items (items), where each item has a name, amount, and category_name.
            
            For the category_name, you MUST choose the best match from the following list of available categories:
            {', '.join(categories) if categories else 'None available'}
            
            IMPORTANT: Your text responses (names, etc.) should primarily be in {lang_name} language where appropriate. Return response in structured JSON.
            """
            
            file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, file_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedReceipt,
                    temperature=0.1,
                )
            )

            if not response or not response.text:
                logger.warning(f"Gemini returned empty response (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise Exception("Empty response from Gemini API (503/Busy)")

            data = json.loads(response.text)
            return ParsedReceipt(**data)

        except Exception as e:
            # Check if it's a 503/504 error to retry
            error_str = str(e)
            if ("503" in error_str or "504" in error_str or "UNAVAILABLE" in error_str) and attempt < max_retries - 1:
                logger.warning(f"Gemini API 503 error (attempt {attempt+1}/{max_retries}). Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2 # Exponential backoff
                continue
                
            logger.error(f"Error parsing receipt with Gemini: {e}")
            raise e # Raise to let handler know it was an API error, not just 'not a receipt'
