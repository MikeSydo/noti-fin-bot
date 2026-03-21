import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from notion_client import Client
from config import settings
from models.account import Account

logger = logging.getLogger(__name__)

class NotionWriter:
    def __init__(self):
        self.client = Client(auth=settings.NOTION_API_KEY)
        self.account_db_id = settings.NOTION_ACCOUNTS_DB_ID

    async def add_account(self, account: Account) -> bool:
        """
        Adding account in Notion DB.

        Args:
            account: Account data.

        Returns:
            True if successful, False otherwise.
        """
        try:
            properties = self.build_account_properties(
                name=account.name,
                initial_amount=account.initial_amount
            )
            self.client.pages.create(
                parent={"account_db_id": self.account_db_id},
                properties=properties,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add manual expense to Notion: {e}")
            return False

    @staticmethod
    def build_account_properties(
            name: str,
            initial_amount: Optional[Decimal] = None
    ) -> dict:
        """Build properties dict for Notion API."""
        properties = {
            "Account": {
                "title": [{"text": {"content": name}}],
            },
            "Initial Amount": {
                "number": initial_amount,
            }
        }

        return properties


notion_writer = NotionWriter()
