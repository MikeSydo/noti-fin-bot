import logging

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
            properties = account.to_notion_properties()
            self.client.pages.create(
                parent={"database_id": self.account_db_id},
                properties=properties,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add manual expense to Notion: {e}")
            return False

notion_writer = NotionWriter()
