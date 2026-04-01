import uuid
from decimal import Decimal
import logging

from notion_client import AsyncClient
from config import settings
from models.account import Account
from models.category import Category
from models.expense import Expense

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
        self.categories_db_id = format_notion_id(settings.NOTION_CATEGORIES_DB_ID)

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
                raw_amount = properties["Initial Amount"]["number"]
                account = Account(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Account",
                    initial_amount=Decimal(str(raw_amount)) if raw_amount is not None else None,
                )
                accounts.append(account)
            return accounts
        except Exception as e:
            logger.error(f"Failed to get accounts from Notion: {e}")
            return []

    async def delete_page(self, page_id: str) -> bool:
        """
        Archive (delete) a page in Notion DB.

        Args:
            page_id: The ID of the page (account, expense, etc.) to delete.

        Returns:
            True if successful, False otherwise.
        """
        try:
            await self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete page from Notion: {e}")
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

    async def get_categories(self) -> list[Category]:
        """
        Get all categories from Notion DB.

        Returns:
            List of categories.
        """
        try:
            response = await self.client.request(
                path=f"databases/{self.categories_db_id}/query",
                method="POST",
                body={}
            )
            categories = []
            for page in response.get("results", []):
                properties = page["properties"]
                title_parts = properties["Category"]["title"]
                raw_monthly_budget = properties["Monthly Budget"]["number"]
                category = Category(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Category",
                    monthly_budget=Decimal(str(raw_monthly_budget)) if raw_monthly_budget is not None else None,
                )
                categories.append(category)
            return categories
        except Exception as e:
            logger.error(f"Failed to get categories from Notion: {e}")
            return []

    async def get_category(self, id: str) -> Category:
        """
        Get category by id from Notion DB.
        Returns: Category object.
        """
        try:
            response = await self.client.request(
                path=f"databases/{self.categories_db_id}/query",
                method="POST",
                body={}
            )
            for page in response.get("results", []):
                properties = page["properties"]
                title_parts = properties["Category"]["title"]
                raw_monthly_budget = properties["Monthly Budget"]["number"]
                if page["id"] == id:
                    return Category(
                        id=page["id"],
                        name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Category",
                        monthly_budget=Decimal(str(raw_monthly_budget)) if raw_monthly_budget is not None else None
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to get category from Notion: {e}")
            return None

    async def get_account(self, id: str) -> Account:
        """
        Get account by id from Notion DB.
        Returns: Account object.
        """
        try:
            response = await self.client.request(
                path=f"databases/{self.accounts_db_id}/query",
                method="POST",
                body={}
            )
            for page in response.get("results", []):
                properties = page["properties"]
                title_parts = properties["Account"]["title"]
                raw_amount = properties["Initial Amount"]["number"]
                if page["id"] == id:
                    return Account(
                        id=page["id"],
                        name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Account",
                        initial_amount=Decimal(str(raw_amount)) if raw_amount is not None else None
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to get account from Notion: {e}")
            return None

    async def find_expenses(self, name: str) -> list[str]:
        """Return found expense id by name from Notion DB."""
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={}
            )
            id_list = []
            for page in response.get("results", []):
                properties = page.get("properties", {})
                title_parts = properties.get("Expense", {}).get("title", [])
                if title_parts and name == title_parts[0]["text"]["content"]:
                    id_list.append(page["id"])
            if id_list is None:
                return None
            return id_list
        except:
            logger.error(f"Failed to find expense from Notion: {name}")
            return None

    async def get_expenses(self, expenses_id: list[str]) -> list[Expense]:
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={}
            )
            expenses = []
            from datetime import datetime
            for page in response.get("results", []):
                if expenses_id is not None and page["id"] not in expenses_id:
                    continue

                properties = page["properties"]
                title_parts = properties.get("Expense", {}).get("title", [])
                raw_amount = properties.get("Amount", {}).get("number")
                date_obj = properties.get("Date", {}).get("date")

                account_rel = properties.get("Account", {}).get("relation", [])
                category_rel = properties.get("Category", {}).get("relation", [])

                account = Account(id=account_rel[0]["id"], name="Unknown Account") if account_rel else None
                category = Category(id=category_rel[0]["id"], name="Unknown Category") if category_rel else None

                expense = Expense(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Expense",
                    amount=Decimal(str(raw_amount)) if raw_amount is not None else Decimal("0.0"),
                    date=date_obj["start"] if date_obj else datetime.now().isoformat(),
                    account=account,
                    category=category,
                )
                expenses.append(expense)
            return expenses
        except Exception as e:
            logger.error(f"Failed to get expenses from Notion: {e}")
            return []

notion_writer = NotionWriter()
