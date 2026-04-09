import uuid
from datetime import datetime
from decimal import Decimal
import logging
from typing import Optional

from notion_client import AsyncClient
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


def _parse_expense_from_page(page: dict) -> Expense:
    """Parse a Notion page into an Expense object. Shared helper to avoid duplication."""
    properties = page["properties"]
    title_parts = properties.get("Expense", {}).get("title", [])
    raw_amount = properties.get("Amount", {}).get("number")
    date_obj = properties.get("Date", {}).get("date")

    account_rel = properties.get("Account", {}).get("relation", [])
    category_rel = properties.get("Category", {}).get("relation", [])

    account = Account(id=account_rel[0]["id"], name="Unknown Account") if account_rel else None
    category = Category(id=category_rel[0]["id"], name="Unknown Category") if category_rel else None

    # Parse date with multiple format support
    if date_obj and date_obj.get("start"):
        date_str = date_obj["start"]
        try:
            parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            parsed_date = datetime.now()
    else:
        parsed_date = datetime.now()

    return Expense(
        id=page["id"],
        name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Expense",
        amount=Decimal(str(raw_amount)) if raw_amount is not None else Decimal("0"),
        date=parsed_date,
        account=account,
        category=category,
    )


class NotionWriter:
    """Per-user Notion API client. Each user gets their own instance with their own access token."""

    def __init__(self, access_token: str, accounts_db_id: str, expenses_db_id: str,
                 group_expenses_db_id: str, categories_db_id: str):
        self.client = AsyncClient(
            auth=access_token,
            notion_version="2022-06-28"
        )
        self.accounts_db_id = format_notion_id(accounts_db_id)
        self.expenses_db_id = format_notion_id(expenses_db_id)
        self.group_expenses_db_id = format_notion_id(group_expenses_db_id)
        self.categories_db_id = format_notion_id(categories_db_id)

    # ──────────────────────────────────────────────
    # Accounts
    # ──────────────────────────────────────────────

    async def add_account(self, account: Account) -> bool:
        """Add an account to the user's Notion DB."""
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
        """Get all accounts from the user's Notion DB."""
        try:
            response = await self.client.request(
                path=f"databases/{self.accounts_db_id}/query",
                method="POST",
                body={}
            )
            accounts = []
            for page in response.get("results", []):
                properties = page["properties"]
                title_parts = properties["Account"]["title"]
                raw_amount = properties.get("Initial Amount", {}).get("number")
                raw_monthly_budget = properties.get("Monthly Budget", {}).get("number")
                account = Account(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Account",
                    initial_amount=Decimal(str(raw_amount)) if raw_amount is not None else None,
                    monthly_budget=Decimal(str(raw_monthly_budget)) if raw_monthly_budget is not None else None,
                )
                accounts.append(account)
            return accounts
        except Exception as e:
            logger.error(f"Failed to get accounts from Notion: {e}")
            return []

    async def get_account(self, id: str) -> Optional[Account]:
        """Get account by id from Notion DB."""
        try:
            response = await self.client.request(
                path=f"databases/{self.accounts_db_id}/query",
                method="POST",
                body={}
            )
            for page in response.get("results", []):
                if page["id"] == id:
                    properties = page["properties"]
                    title_parts = properties["Account"]["title"]
                    raw_amount = properties.get("Initial Amount", {}).get("number")
                    raw_monthly_budget = properties.get("Monthly Budget", {}).get("number")
                    return Account(
                        id=page["id"],
                        name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Account",
                        initial_amount=Decimal(str(raw_amount)) if raw_amount is not None else None,
                        monthly_budget=Decimal(str(raw_monthly_budget)) if raw_monthly_budget is not None else None,
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to get account from Notion: {e}")
            return None

    async def delete_page(self, page_id: str) -> bool:
        """Archive (delete) a page in Notion DB."""
        try:
            await self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete page from Notion: {e}")
            return False

    # ──────────────────────────────────────────────
    # Expenses
    # ──────────────────────────────────────────────

    async def add_expense(self, expense: Expense) -> str | None:
        """Add expense to the user's Notion DB. Returns page ID or None."""
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

    async def find_expenses(self, name: str) -> list[str] | None:
        """Find expense IDs by name."""
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
            return id_list if id_list else None
        except Exception as e:
            logger.error(f"Failed to find expense from Notion: {e}")
            return None

    async def get_expenses(self, expenses_id: list[str]) -> list[Expense]:
        """Get expenses by IDs."""
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={}
            )
            expenses = []
            for page in response.get("results", []):
                if expenses_id is not None and page["id"] not in expenses_id:
                    continue
                expenses.append(_parse_expense_from_page(page))
            return expenses
        except Exception as e:
            logger.error(f"Failed to get expenses from Notion: {e}")
            return []

    async def get_expenses_list(self) -> list[Expense]:
        """Get all expenses (used for multi-select in group expenses)."""
        return await self.get_recent_expenses(limit=50)

    async def get_recent_expenses(self, limit: int = 15) -> list[Expense]:
        """Get the most recent expenses."""
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={
                    "page_size": limit,
                    "sorts": [{"property": "Date", "direction": "descending"}]
                }
            )
            return [_parse_expense_from_page(page) for page in response.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get recent expenses from Notion: {e}")
            return []

    async def get_all_expenses(self) -> list[Expense]:
        """Get all expenses."""
        try:
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={}
            )
            return [_parse_expense_from_page(page) for page in response.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to get all expenses from Notion: {e}")
            return []

    async def get_expenses_by_date_range(self, start_date: datetime, end_date: datetime) -> list[Expense]:
        """Get expenses within a specific date range."""
        try:
            logger.info(f"Fetching expenses from {start_date} to {end_date}")
            response = await self.client.request(
                path=f"databases/{self.expenses_db_id}/query",
                method="POST",
                body={
                    "filter": {
                        "and": [
                            {"property": "Date", "date": {"on_or_after": start_date.strftime('%Y-%m-%d')}},
                            {"property": "Date", "date": {"on_or_before": end_date.strftime('%Y-%m-%d')}},
                        ]
                    },
                    "sorts": [{"property": "Date", "direction": "descending"}]
                }
            )
            return [_parse_expense_from_page(page) for page in response.get("results", [])]
        except Exception as e:
            logger.error(f"Failed to retrieve expenses for date range: {e}")
            return []

    # ──────────────────────────────────────────────
    # Categories
    # ──────────────────────────────────────────────

    async def get_categories(self) -> list[Category]:
        """Get all categories from Notion DB."""
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
                category = Category(
                    id=page["id"],
                    name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Category",
                )
                categories.append(category)
            return categories
        except Exception as e:
            logger.error(f"Failed to get categories from Notion: {e}")
            return []

    async def get_category(self, id: str) -> Optional[Category]:
        """Get category by id from Notion DB."""
        try:
            response = await self.client.request(
                path=f"databases/{self.categories_db_id}/query",
                method="POST",
                body={}
            )
            for page in response.get("results", []):
                if page["id"] == id:
                    properties = page["properties"]
                    title_parts = properties["Category"]["title"]
                    return Category(
                        id=page["id"],
                        name=title_parts[0]["text"]["content"] if title_parts else "Unnamed Category",
                    )
            return None
        except Exception as e:
            logger.error(f"Failed to get category from Notion: {e}")
            return None

    # ──────────────────────────────────────────────
    # Group Expenses
    # ──────────────────────────────────────────────

    async def add_group_expense(self, group_expense: GroupExpense) -> bool:
        """Add group expense to the user's Notion DB."""
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

    async def find_group_expenses(self, name: str) -> list[str] | None:
        """Find group expense IDs by name."""
        try:
            response = await self.client.request(
                path=f"databases/{self.group_expenses_db_id}/query",
                method="POST",
                body={
                    "filter": {
                        "property": "Group Expense",
                        "title": {"contains": name}
                    }
                }
            )
            result = [r["id"] for r in response.get("results", [])]
            return result if result else None
        except Exception as e:
            logger.error(f"Failed to find group expense from Notion: {e}")
            return None

    async def get_group_expenses(self, expenses_id: list[str]) -> list[GroupExpense]:
        """Get group expenses by IDs (fetches each page individually)."""
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

                expenses_relations = []
                if "Expenses" in properties and properties["Expenses"]["relation"]:
                    expenses_relations = [rel["id"] for rel in properties["Expenses"]["relation"]]

                expense_dict = {
                    "id": response["id"],
                    "name": properties["Group Expense"]["title"][0]["text"]["content"] if properties["Group Expense"]["title"] else "",
                    "amount": Decimal(str(properties["Amount"]["number"])) if properties["Amount"]["number"] is not None else Decimal('0'),
                    "date": datetime.fromisoformat(properties["Date"]["date"]["start"]) if properties["Date"]["date"] else datetime.now(),
                    "account": account,
                    "category": category,
                    "receipt_url": receipt_url,
                    "expenses_relations": expenses_relations
                }
                group_expenses.append(GroupExpense.model_validate(expense_dict))
            return group_expenses
        except Exception as e:
            logger.error(f"Failed to get group expenses from Notion: {e}")
            return []

    # Alias used by group_expenses handler
    async def get_group_expenses_by_ids(self, expenses_id: list[str]) -> list[GroupExpense]:
        """Alias for get_group_expenses (used by handlers)."""
        return await self.get_group_expenses(expenses_id)


async def get_notion_writer(telegram_id: int) -> Optional[NotionWriter]:
    """
    Factory function: create a per-user NotionWriter instance.
    Retrieves user credentials from DB, decrypts access token, and returns a configured writer.
    Returns None if user has no Notion connection or missing database IDs.
    """
    from services.user_service import get_user
    from services.security import decrypt_token

    user = await get_user(telegram_id)
    if not user or not user.is_notion_connected or not user.has_databases:
        return None

    access_token = decrypt_token(user.notion_access_token_encrypted)
    if not access_token:
        return None

    return NotionWriter(
        access_token=access_token,
        accounts_db_id=user.accounts_db_id,
        expenses_db_id=user.expenses_db_id,
        group_expenses_db_id=user.group_expenses_db_id,
        categories_db_id=user.categories_db_id,
    )