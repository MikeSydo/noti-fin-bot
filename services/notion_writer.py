import uuid
from datetime import datetime
from decimal import Decimal
import logging

from notion_client import AsyncClient
from config import settings
from models.account import Account
from models.category import Category
from models.expense import Expense
from models.group_expense import GroupExpense

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
        self.group_expenses_db_id = format_notion_id(settings.NOTION_GROUP_EXPENSES_DB_ID)
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

    async def add_expense(self, expense: Expense) -> str | None:
        """
        Adding expense in Notion DB.

        Args:
            expense: Expsense data.

        Returns:
            ID of the created expense if successful, None otherwise.
        """

        try:
            properties = expense.to_notion_properties()
            response = await self.client.pages.create(
                parent={"database_id": self.expenses_db_id},
                properties=properties,
            )
            return response["id"]
        except Exception as e:
            logger.error(f"Failed to add expense to Notion: {e}")
            return None

    async def add_group_expense(self, group_expense: GroupExpense) -> bool:
        """
        Adding group expense in Notion DB.

        Args:
            group_expense: GroupExpense data.

        Returns:
            True if successful, False otherwise.
        """
        try:
            properties = group_expense.to_notion_properties()
            await self.client.pages.create(
                parent={"database_id": self.group_expenses_db_id},
                properties=properties,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add group expense to Notion: {e}")
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
        """
        Find expenses by name.

        Args:
            name: Expense name.

        Returns:
            List of expense notion ids.
        """
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
        except Exception as e:
            logger.error(f"Failed to find expense from Notion: {e}")
            return None

    async def find_group_expenses(self, name: str) -> list[str]:
        """
        Find group expenses by name.

        Args:
            name: Group Expense name.

        Returns:
            List of group expenses notion ids.
        """
        try:
            response = await self.client.request(
                path=f"databases/{self.group_expenses_db_id}/query",
                method="POST",
                body={
                    "filter": {
                        "property": "Group Expense",
                        "title": {
                            "contains": name
                        }
                    }
                }
            )
            return [result["id"] for result in response.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to find group expense from Notion: {e}")
            return None

    async def get_expenses(self, expenses_id: list[str]) -> list[Expense]:
        """
        Get expenses by ids.

        Args:
            expenses_id: List of expense ids.

        Returns:
            List of Expense objects.
        """
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

    async def get_recent_expenses(self, limit: int = 15) -> list[Expense]:
        """
        Get the most recent regular expenses.
        
        Args:
            limit: Maximum number of expenses to retrieve.
        
        Returns:
            List of Expense objects.
        """
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={
                    "page_size": limit,
                    "sorts": [
                        {
                            "property": "Date",
                            "direction": "descending"
                        }
                    ]
                }
            )
            expenses = []
            from datetime import datetime
            for page in response.get("results", []):
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
            logger.error(f"Failed to get recent expenses from Notion: {e}")
            return []

    async def get_group_expenses(self, expenses_id: list[str]) -> list[GroupExpense]:
        """
        Get group expenses by ids.

        Args:
            expenses_id: List of group expense ids.

        Returns:
            List of GroupExpense objects.
        """
        try:
            group_expenses = []
            for expense_id in expenses_id:
                response = await self.client.pages.retrieve(page_id=expense_id)
                properties = response["properties"]

                account_id, category_id = None, None
                if "Account" in properties and properties["Account"]["relation"]:
                    account_id = properties["Account"]["relation"][0]["id"]
                if "Category" in properties and properties["Category"]["relation"]:
                    category_id = properties["Category"]["relation"][0]["id"]

                receipt_url = None
                if "Receipt" in properties and properties["Receipt"]["files"]:
                    file_info = properties["Receipt"]["files"][0]
                    if file_info["type"] == "external":
                        receipt_url = file_info["external"]["url"]
                    elif file_info["type"] == "file":
                        receipt_url = file_info["file"]["url"]

                account = await self.get_account(account_id) if account_id else None
                category = await self.get_category(category_id) if category_id else None

                expense_dict = {
                    "id": response["id"],
                    "name": properties["Group Expense"]["title"][0]["text"]["content"] if properties["Group Expense"]["title"] else "",
                    "amount": Decimal(str(properties["Amount"]["number"])) if properties["Amount"]["number"] is not None else Decimal('0'),
                    "date": datetime.fromisoformat(properties["Date"]["date"]["start"]) if properties["Date"]["date"] else datetime.now(),
                    "account": account,
                    "category": category,
                    "receipt_url": receipt_url
                }
                group_expenses.append(GroupExpense.model_validate(expense_dict))
            return group_expenses
        except Exception as e:
            logger.error(f"Failed to get group expenses from Notion: {e}")
            return []

    async def get_expenses_by_date_range(self, start_date: datetime, end_date: datetime) -> list[Expense]:
        """
        Get the expenses within a specific date range.
        """
        try:
            logger.info(f"Fetching expenses from {start_date} to {end_date}")
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={
                    "filter": {
                        "and": [
                            {
                                "property": "Date",
                                "date": {
                                    "on_or_after": start_date.strftime('%Y-%m-%d')
                                }
                            },
                            {
                                "property": "Date",
                                "date": {
                                    "on_or_before": end_date.strftime('%Y-%m-%d')
                                }
                            }
                        ]
                    },
                    "sorts": [
                        {
                            "property": "Date",
                            "direction": "descending"
                        }
                    ]
                }
            )
            expenses = []
            for page in response.get("results", []):
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
                    amount=Decimal(str(raw_amount)) if raw_amount is not None else Decimal("0"),
                    date=datetime.fromisoformat(date_obj["start"].replace("Z", "+00:00")) if date_obj else datetime.now(),
                    account=account,
                    category=category
                )
                expenses.append(expense)
            return expenses
        except Exception as e:
            logger.error(f"Failed to retrieve expenses for date range: {e}")
            return []

notion_writer = NotionWriter()