from decimal import Decimal
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

    async def get_accounts(self) -> list[Account]:
        """
        Get all accounts from Notion DB.

        Returns:
            List of accounts.
        """
        try:
            response = self.client.databases.query(
                database_id=self.account_db_id,
            )
            accounts = []
            for page in response["results"]:
                properties = page["properties"]
                account = Account(
                    id=page["id"],
                    name=properties["Account"]["title"][0]["text"]["content"],
                    initial_amount=Decimal(properties["Initial Amount"]["number"]),
                )
                accounts.append(account)
            return accounts
        except Exception as e:
            logger.error(f"Failed to get accounts from Notion: {e}")
            return []

    async def delete_account(self, account_id: str) -> bool:
        """
        Deleting account in Notion DB.

        Args:
            account_id: Account ID.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.client.pages.update(
                page_id=account_id,
                properties={
                    "Status": {
                        "select": {
                            "name": "Deleted"
                        }
                    }
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete account from Notion: {e}")
            return False

notion_writer = NotionWriter()
