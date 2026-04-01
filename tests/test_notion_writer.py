import pytest
import sys
import os
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.account import Account
from models.expense import Expense
from models.category import Category
from services.notion_writer import NotionWriter

@pytest.fixture
def mock_accounts_response():
    return {
        "results": [
            {
                "id": "uuid_account_1",
                "properties": {
                    "Account": {"title": [{"text": {"content": "Monobank"}}]},
                    "Initial Amount": {"number": 1500.50}
                }
            },
            {
                "id": "uuid_account_2",
                "properties": {
                    "Account": {"title": [{"text": {"content": "Готівка"}}]},
                    "Initial Amount": {"number": None}
                }
            }
        ]
    }

@pytest.fixture
def mock_categories_response():
    return {
        "results": [
            {
                "id": "uuid_category_1",
                "properties": {
                    "Category": {"title": [{"text": {"content": "Products"}}]},
                    "Monthly Budget": {"number": 1500.50}
                }
            },
            {
                "id": "uuid_category_2",
                "properties": {
                    "Category": {"title": [{"text": {"content": "Technology"}}]},
                    "Monthly Budget": {"number": None}
                }
            }
        ]
    }

@pytest.fixture
def mock_expenses_response():
    return {
        "results": [
            {
                "id": "uuid_expense_1",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Groceries"}}]},
                    "Amount": {"number": 500.0},
                    "Date": {"date": {"start": "2024-03-01T10:00:00"}},
                    "Account": {"relation": [{"id": "uuid_account_1"}]},
                    "Category": {"relation": [{"id": "uuid_category_1"}]}
                }
            },
            {
                "id": "uuid_expense_2",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Internet"}}]},
                    "Amount": {"number": 200.0},
                    "Date": {"date": {"start": "2024-03-02T12:00:00"}},
                    "Account": {"relation": [{"id": "uuid_account_1"}]},
                    "Category": {"relation": [{"id": "uuid_category_2"}]}
                }
            },
            {
                "id": "uuid_expense_3",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Coffee"}}]},
                    "Amount": {"number": 50.0},
                    "Date": {"date": {"start": "2024-03-03T09:30:00"}},
                    "Account": {"relation": [{"id": "uuid_account_2"}]},
                    "Category": {"relation": []}
                }
            },
            {
                "id": "uuid_expense_4",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Cinema"}}]},
                    "Amount": {"number": 300.0},
                    "Date": {"date": {"start": "2024-03-04T19:00:00"}},
                    "Account": {"relation": []},
                    "Category": {"relation": [{"id": "uuid_category_2"}]}
                }
            },
            {
                "id": "uuid_expense_5",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Taxi"}}]},
                    "Amount": {"number": 150.0},
                    "Date": {"date": {"start": "2024-03-05T22:15:00"}},
                    "Account": {"relation": []},
                    "Category": {"relation": []}
                }
            },
            {
                "id": "uuid_expense_6",
                "properties": {
                    "Expense": {"title": [{"text": {"content": "Coffee"}}]},
                    "Amount": {"number": 50.0},
                    "Date": {"date": {"start": "2024-03-04T09:30:00"}},
                    "Account": {"relation": [{"id": "uuid_account_2"}]},
                    "Category": {"relation": []}
                }
            },
            {
                "id": "uuid_expense_7",
                "properties": {
                    "Expense": {"title": []},
                    "Amount": {"number": None},
                    "Date": {"date": None},
                    "Account": {"relation": []},
                    "Category": {"relation": []}
                }
            },
        ]
    }

@pytest.fixture
def mock_writer():
    """Create a mock notion writer"""
    with patch('services.notion_writer.AsyncClient') as MockAsyncClient:
        mock_client_instance = MockAsyncClient.return_value
        writer = NotionWriter()
        writer.client = mock_client_instance
        writer.accounts_db_id = "test_db_id"
        yield writer, mock_client_instance

@pytest.mark.asyncio
@pytest.mark.parametrize("expected_name, expected_amount", [
    ("Monobank", Decimal("1500.50")),
    ("PrivatBank", None),
])
async def test_add_account_success(mock_writer, expected_name, expected_amount):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(return_value={})

    test_account = Account(name=expected_name, initial_amount=expected_amount)

    result = await writer.add_account(test_account)

    assert result is True

    mock_client.pages.create.assert_called_once()
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "test_db_id"}
    
    assert call_kwargs["properties"] == test_account.to_notion_properties()

    account_title = call_kwargs["properties"]["Account"]["title"][0]["text"]["content"]
    assert account_title == expected_name

@pytest.mark.asyncio
async def test_add_account_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(side_effect=Exception("API Error"))
    
    test_account = Account(name="ErrorBank", initial_amount=Decimal("100.00"))
    result = await writer.add_account(test_account)
    
    assert result is False
    mock_client.pages.create.assert_called_once()

@pytest.mark.asyncio
async def test_delete_account_success(mock_writer, mock_accounts_response):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(return_value={})

    result = await writer.delete_account("uuid_account_1")

    assert result is True
    mock_client.pages.update.assert_called_once_with(
        page_id="uuid_account_1",
        archived=True
    )

@pytest.mark.asyncio
async def test_delete_account_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.delete_account("uuid_account_1")
    
    assert result is False
    mock_client.pages.update.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("account_id, expected_name, expected_amount", [
    ("uuid_account_1", "Monobank", Decimal("1500.50")),
    ("uuid_account_2", "Готівка", None),
])
async def test_get_account_success(mock_writer, mock_accounts_response, account_id, expected_name, expected_amount):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_accounts_response)

    account = await writer.get_account(account_id)

    assert account.id == account_id
    assert account.name == expected_name
    assert account.initial_amount == expected_amount

@pytest.mark.asyncio
async def test_get_account_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    account = await writer.get_account("fake_uuid")
    
    assert account is None
    mock_client.request.assert_called_once()

@pytest.mark.asyncio
async def test_get_accounts_success(mock_writer, mock_accounts_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_accounts_response)

    accounts = await writer.get_accounts()

    assert len(accounts) == 2
    assert accounts[0].id == "uuid_account_1"
    assert accounts[0].initial_amount == Decimal("1500.50")
    assert accounts[1].id == "uuid_account_2"
    assert accounts[1].initial_amount is None

    mock_client.request.assert_called_once_with(
        path="databases/test_db_id/query",
        method="POST",
        body={}
    )

@pytest.mark.asyncio
async def test_get_accounts_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    accounts = await writer.get_accounts()
    
    assert accounts == []
    mock_client.request.assert_called_once()

@pytest.mark.asyncio
async def test_get_categories_success(mock_writer, mock_categories_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_categories_response)

    categories = await writer.get_categories()

    assert len(categories) == 2
    assert categories[0].id == "uuid_category_1"
    assert categories[0].monthly_budget == Decimal("1500.50")
    assert categories[1].id == "uuid_category_2"
    assert categories[1].monthly_budget is None

@pytest.mark.asyncio
async def test_get_categories_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    categories = await writer.get_categories()
    
    assert categories == []
    mock_client.request.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("account_input, category_input", [
    (Account(id="acc_1", name="Monobank", initial_amount=Decimal("1500.50")), Category(id="cat_1", name="Test Category", monthly_budget=Decimal("5000.00"))),
    (None, None),
])
async def test_add_expense_success(mock_writer, account_input, category_input):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(return_value={})
    writer.expenses_db_id = "test_expenses_db_id"
    
    test_expense = Expense(
        name="Groceries",
        amount=Decimal("500.00"),
        date=datetime.now(),
        account=account_input,
        category=category_input
    )

    result = await writer.add_expense(test_expense)

    assert result is True
    mock_client.pages.create.assert_called_once()
    
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "test_expenses_db_id"}
    assert call_kwargs["properties"] == test_expense.to_notion_properties()

@pytest.mark.asyncio
@pytest.mark.parametrize("account_input, category_input", [
    (Account(id="acc_1", name="Monobank", initial_amount=Decimal("1500.50")), Category(id="cat_1", name="Test Category", monthly_budget=Decimal("5000.00"))),
    (None, None),
])
async def test_add_expense_failure(mock_writer, account_input, category_input):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(side_effect=Exception("API Error"))
    
    test_expense = Expense(
        name="Groceries",
        amount=Decimal("500.00"),
        date=datetime.now(),
        account=account_input,
        category=category_input
    )

    result = await writer.add_expense(test_expense)
    
    assert result is False
    mock_client.pages.create.assert_called_once()

@pytest.mark.asyncio
async def test_find_expenses_success(mock_writer, mock_expenses_response):
    writer, mock_client = mock_writer
    writer.expenses_db_id = "test_expenses_db_id"
    mock_client.request = AsyncMock(return_value=mock_expenses_response)

    expenses_id = await writer.find_expenses("Coffee")

    assert expenses_id[0] == "uuid_expense_3"
    assert expenses_id[1] == "uuid_expense_6"

    mock_client.request.assert_called_with(
        path="databases/test_expenses_db_id/query",
        method="POST",
        body={}
    )

@pytest.mark.asyncio
async def test_find_expenses_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.find_expenses("Coffee")

    assert result is None
    mock_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_get_expense_success(mock_writer, mock_expenses_response):
    writer, mock_client = mock_writer
    writer.expenses_db_id = "test_expenses_db_id"
    mock_client.request = AsyncMock(return_value=mock_expenses_response)

    expenses = await writer.get_expenses(["uuid_expense_2", "uuid_expense_7"])

    assert len(expenses) == 2
    assert expenses[0].id == "uuid_expense_2"
    assert expenses[1].id == "uuid_expense_7"
    assert expenses[1].name == "Unnamed Expense"
    assert expenses[1].amount == Decimal("0.0")
    assert expenses[1].account is None
    assert expenses[1].category is None

    mock_client.request.assert_called_with(
        path="databases/test_expenses_db_id/query",
        method="POST",
        body={}
    )

@pytest.mark.asyncio
async def test_get_expense_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    expenses = await writer.get_expenses(["uuid_expense_2"])

    assert expenses == []
    mock_client.request.assert_called_once()

@pytest.mark.asyncio
async def test_delete_expense_success(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(return_value={})

    result = await writer.delete_expense("uuid_expense_1")

    assert result is True
    mock_client.pages.update.assert_called_once_with(
        page_id="uuid_expense_1",
        archived=True
    )

@pytest.mark.asyncio
async def test_delete_expense_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.delete_expense("uuid_expense_1")
    
    assert result is False
    mock_client.pages.update.assert_called_once()