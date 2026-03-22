import uuid
from decimal import Decimal
import logging

from notion_client import AsyncClient
from config import settings
from models.account import Account
from models.expenses import Expense

logger = logging.getLogger(__name__)

def format_notion_id(notion_id: str) -> str:
    """Format a Notion ID to include hyphens if it doesn't already."""
    if "-" not in notion_id and len(notion_id) == 32:
        return str(uuid.UUID(notion_id))
    return notion_id

class NotionWriter:
    def __init__(self):
        self.client = AsyncClient(
            auth=settings.NOTION_API_KEY,
            notion_version="2022-06-28"
        )
        self.accounts_db_id = format_notion_id(settings.NOTION_ACCOUNTS_DB_ID)
        self.expenses_db_id = format_notion_id(settings.NOTION_EXPENSES_DB_ID)

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
            await self.client.pages.create(
                parent={"database_id": self.accounts_db_id},
                properties=properties,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add account to Notion: {e}")
            return False

    async def get_accounts(self) -> list[Account]:
        """
        Get all accounts from Notion DB.

        Returns:
            List of accounts.
        """
        try:
            # Using request directly since notion-client 3.0.0 removed database.query endpoint helper
            response = await self.client.request(
                path=f"databases/{self.accounts_db_id}/query",
                method="POST",
                body={}
            )
            accounts = []
            for page in response.get("results", []):
                properties = page["properties"]
                title_parts = properties["Account"]["title"]
                account = Account(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Account",
                    initial_amount=Decimal(str(properties["Initial Amount"]["number"] or 0)),
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
            await self.client.pages.update(
                page_id=account_id,
                archived=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete account from Notion: {e}")
            return False

    async def add_expense(self, expense: Expense) -> bool:
        """
        Adding expense in Notion DB.

        Args:
            expense: Expsense data.

        Returns:
            True if successful, False otherwise.
        """

        try:
            properties = expense.to_notion_properties()
            await self.client.pages.create(
                parent={"database_id": self.expenses_db_id},
                properties=properties,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add expense to Notion: {e}")
            return False

    #TODO: add func get categories

notion_writer = NotionWriter()
