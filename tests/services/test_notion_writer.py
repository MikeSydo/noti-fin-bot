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
def mock_group_expenses_response():
    return {
        "results": [
            {
                "id": "uuid_grexpense_1",
                "properties": {
                    "Group Expense": {"title": [{"text": {"content": "Party"}}]},
                    "Amount": {"number": 1500.0},
                    "Date": {"date": {"start": "2024-03-01T10:00:00"}},
                    "Account": {"relation": [{"id": "uuid_account_1"}]},
                    "Category": {"relation": [{"id": "uuid_category_1"}]},
                    "Receipt": {"files": [{"type": "external", "external": {"url": "http://example.com/receipt.jpg"}}]}
                }
            },
        ]
    }

@pytest.fixture
def mock_writer():
    """Create a mock notion writer"""
    with patch('services.notion_writer.AsyncClient') as MockAsyncClient:
        mock_client_instance = MockAsyncClient.return_value
        writer = NotionWriter(
            access_token="fake_token", 
            accounts_db_id="test_db_id", 
            expenses_db_id="test_expenses_db_id", 
            group_expenses_db_id="test_group_expenses_db_id", 
            categories_db_id="test_categories_db_id"
        )
        writer.client = mock_client_instance
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

    result = await writer.delete_page("uuid_account_1")

    assert result is True
    mock_client.pages.update.assert_called_once_with(
        page_id="uuid_account_1",
        archived=True
    )

@pytest.mark.asyncio
async def test_delete_account_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.delete_page("uuid_account_1")

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
    assert categories[0].name == "Products"
    assert categories[1].id == "uuid_category_2"

@pytest.mark.asyncio
async def test_get_categories_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    categories = await writer.get_categories()
    
    assert categories == []
    mock_client.request.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("account_input, category_input", [
    (Account(id="acc_1", name="Monobank", initial_amount=Decimal("1500.50"), monthly_budget=Decimal("5000.00")), Category(id="cat_1", name="Test Category")),
    (None, None),
])
async def test_add_expense_success(mock_writer, account_input, category_input):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(return_value={"id": "new_expense_id_123"})
    writer.expenses_db_id = "test_expenses_db_id"
    
    test_expense = Expense(
        name="Groceries",
        amount=Decimal("500.00"),
        date=datetime.now(),
        account=account_input,
        category=category_input
    )

    result = await writer.add_expense(test_expense)

    assert result == "new_expense_id_123"
    mock_client.pages.create.assert_called_once()
    
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "test_expenses_db_id"}
    assert call_kwargs["properties"] == test_expense.to_notion_properties()

@pytest.mark.asyncio
async def test_add_group_expense_success(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(return_value={})
    writer.group_expenses_db_id = "test_group_expenses_db_id"
    
    from models.group_expense import GroupExpense
    test_expense = GroupExpense(
        name="Party",
        amount=Decimal("1500.00"),
        date=datetime.now(),
        account=None,
        category=None,
        receipt_url="http://example.com/receipt.jpg"
    )

    result = await writer.add_group_expense(test_expense)

    assert result is True
    mock_client.pages.create.assert_called_once()
    
    call_kwargs = mock_client.pages.create.call_args.kwargs
    assert call_kwargs["parent"] == {"database_id": "test_group_expenses_db_id"}
    assert call_kwargs["properties"] == test_expense.to_notion_properties()

@pytest.mark.asyncio
async def test_add_group_expense_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.create = AsyncMock(side_effect=Exception("API Error"))
    
    from models.group_expense import GroupExpense
    test_expense = GroupExpense(
        name="Party error",
        amount=Decimal("1500.00"),
        date=datetime.now(),
        account=None,
        category=None,
        receipt_url="http://example.com/receipt.jpg"
    )

    result = await writer.add_group_expense(test_expense)
    
    assert result is False
    mock_client.pages.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_group_expenses_success(mock_writer, mock_group_expenses_response):
    writer, mock_client = mock_writer
    
    page_data = mock_group_expenses_response["results"][0]
    # Add Expenses relation data
    page_data["properties"]["Expenses"] = {"relation": [{"id": "uuid_expense_1"}, {"id": "uuid_expense_2"}]}
    
    mock_client.pages.retrieve = AsyncMock(return_value=page_data)

    expenses = await writer.get_group_expenses(["uuid_grexpense_1"])

    assert len(expenses) == 1
    assert expenses[0].id == "uuid_grexpense_1"
    assert expenses[0].name == "Party"
    assert expenses[0].amount == Decimal("1500.0")
    assert expenses[0].expenses_relations == ["uuid_expense_1", "uuid_expense_2"]

    mock_client.pages.retrieve.assert_called_once_with(page_id="uuid_grexpense_1")

@pytest.mark.asyncio
@pytest.mark.parametrize("account_input, category_input", [
    (Account(id="acc_1", name="Monobank", initial_amount=Decimal("1500.50"), monthly_budget=Decimal("5000.00")), Category(id="cat_1", name="Test Category")),
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
    
    assert result is None
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

    result = await writer.delete_page("uuid_expense_1")

    assert result is True
    mock_client.pages.update.assert_called_once_with(
        page_id="uuid_expense_1",
        archived=True
    )

@pytest.mark.asyncio
async def test_delete_expense_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.pages.update = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.delete_page("uuid_expense_1")
    
    assert result is False
    mock_client.pages.update.assert_called_once()

@pytest.mark.asyncio
async def test_get_expenses_by_date_range_success(mock_writer, mock_expenses_response):
    writer, mock_client = mock_writer
    writer.expenses_db_id = "test_expenses_db_id"

    # Mock the response as if the Notion API has already filtered them for 2024-03-01 - 2024-03-04
    # and sorted them in descending order (Date descending)
    sorted_mock_results = [
        mock_expenses_response["results"][3],  # 2024-03-04T19:00:00 (uuid_expense_4)
        mock_expenses_response["results"][5],  # 2024-03-04T09:30:00 (uuid_expense_6)
        mock_expenses_response["results"][2],  # 2024-03-03T09:30:00 (uuid_expense_3)
        mock_expenses_response["results"][1],  # 2024-03-02T12:00:00 (uuid_expense_2)
        mock_expenses_response["results"][0],  # 2024-03-01T10:00:00 (uuid_expense_1)
    ]

    mock_client.request = AsyncMock(return_value={"results": sorted_mock_results})

    start_date = datetime(2024, 3, 1)
    end_date = datetime(2024, 3, 4)
    expenses = await writer.get_expenses_by_date_range(start_date, end_date)

    # Check the number of results
    assert len(expenses) == 5

    # Check that all required expenses were fetched and in the correct order
    expected_ids = ["uuid_expense_4", "uuid_expense_6", "uuid_expense_3", "uuid_expense_2", "uuid_expense_1"]
    assert [exp.id for exp in expenses] == expected_ids

    # Check that dates converted correctly and are in descending order
    dates = [exp.date for exp in expenses]
    assert dates == sorted(dates, reverse=True)

    mock_client.request.assert_called_once()
    called_kwargs = mock_client.request.call_args.kwargs
    assert called_kwargs["method"] == "POST"

    # Check the filter payload
    filter_payload = called_kwargs["body"]["filter"]["and"]
    assert len(filter_payload) == 2
    assert filter_payload[0]["date"]["on_or_after"] == start_date.strftime('%Y-%m-%d')
    assert filter_payload[1]["date"]["on_or_before"] == end_date.strftime('%Y-%m-%d')

    # Check the sorts payload
    assert "sorts" in called_kwargs["body"]
    sorts_payload = called_kwargs["body"]["sorts"]
    assert sorts_payload[0]["property"] == "Date"
    assert sorts_payload[0]["direction"] == "descending"

@pytest.mark.asyncio
async def test_get_expenses_by_date_range_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    start_date = datetime(2026, 4, 1)
    end_date = datetime(2026, 4, 2)
    expenses = await writer.get_expenses_by_date_range(start_date, end_date)

    assert expenses == []
    mock_client.request.assert_called_once()


# ─────────────────────────────────────────────
# Group Expenses – find / get / delete
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_group_expenses_success(mock_writer, mock_group_expenses_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_group_expenses_response)

    ids = await writer.find_group_expenses("Party")

    assert ids is not None
    assert "uuid_grexpense_1" in ids
    mock_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_find_group_expenses_not_found(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value={"results": []})

    ids = await writer.find_group_expenses("Nonexistent")

    assert ids is None


@pytest.mark.asyncio
async def test_find_group_expenses_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    ids = await writer.find_group_expenses("Party")

    assert ids is None


@pytest.mark.asyncio
async def test_get_group_expenses_success_with_relations(mock_writer, mock_group_expenses_response):
    """Test that get_group_expenses correctly parses expenses_relations from Notion response."""
    writer, mock_client = mock_writer

    page_data = mock_group_expenses_response["results"][0]
    page_data["properties"]["Expenses"] = {
        "relation": [{"id": "uuid_expense_1"}, {"id": "uuid_expense_2"}]
    }
    mock_client.pages.retrieve = AsyncMock(return_value=page_data)

    result = await writer.get_group_expenses(["uuid_grexpense_1"])

    assert len(result) == 1
    assert result[0].id == "uuid_grexpense_1"
    assert result[0].name == "Party"
    assert "uuid_expense_1" in result[0].expenses_relations
    assert "uuid_expense_2" in result[0].expenses_relations


@pytest.mark.asyncio
async def test_get_group_expenses_no_relations(mock_writer, mock_group_expenses_response):
    """Test that get_group_expenses returns empty expenses_relations when property is absent."""
    writer, mock_client = mock_writer

    page_data = mock_group_expenses_response["results"][0]
    # Ensure no Expenses relation key present
    page_data["properties"].pop("Expenses", None)
    mock_client.pages.retrieve = AsyncMock(return_value=page_data)

    result = await writer.get_group_expenses(["uuid_grexpense_1"])

    assert len(result) == 1
    assert result[0].expenses_relations == []


@pytest.mark.asyncio
async def test_get_group_expenses_failure(mock_writer):
    """Test that get_group_expenses returns empty list on API error."""
    writer, mock_client = mock_writer
    mock_client.pages.retrieve = AsyncMock(side_effect=Exception("API Error"))

    result = await writer.get_group_expenses(["uuid_grexpense_1"])

    assert result == []


@pytest.mark.asyncio
async def test_get_group_expenses_by_ids_alias(mock_writer, mock_group_expenses_response):
    """Test that get_group_expenses_by_ids is an alias for get_group_expenses."""
    writer, mock_client = mock_writer

    page_data = mock_group_expenses_response["results"][0]
    page_data["properties"]["Expenses"] = {"relation": []}
    mock_client.pages.retrieve = AsyncMock(return_value=page_data)

    result = await writer.get_group_expenses_by_ids(["uuid_grexpense_1"])

    assert len(result) == 1
    assert result[0].id == "uuid_grexpense_1"


# ─────────────────────────────────────────────
# Expenses – get_all, get_recent, get_list
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_expenses_success(mock_writer, mock_expenses_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_expenses_response)

    expenses = await writer.get_all_expenses()

    assert len(expenses) == 7
    mock_client.request.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_expenses_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    expenses = await writer.get_all_expenses()

    assert expenses == []


@pytest.mark.asyncio
async def test_get_recent_expenses_success(mock_writer, mock_expenses_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_expenses_response)

    expenses = await writer.get_recent_expenses(limit=5)

    assert len(expenses) > 0
    call_kwargs = mock_client.request.call_args.kwargs
    # Should request with page_size & sorts
    assert call_kwargs["body"]["page_size"] == 5
    assert call_kwargs["body"]["sorts"][0]["property"] == "Date"


@pytest.mark.asyncio
async def test_get_recent_expenses_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    expenses = await writer.get_recent_expenses()

    assert expenses == []


@pytest.mark.asyncio
async def test_get_expenses_list_delegates_to_recent(mock_writer, mock_expenses_response):
    """Test that get_expenses_list calls get_recent_expenses with limit=50."""
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_expenses_response)

    await writer.get_expenses_list()

    call_kwargs = mock_client.request.call_args.kwargs
    assert call_kwargs["body"]["page_size"] == 50


# ─────────────────────────────────────────────
# Categories – get_category by id
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_category_success(mock_writer, mock_categories_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_categories_response)

    category = await writer.get_category("uuid_category_1")

    assert category is not None
    assert category.id == "uuid_category_1"
    assert category.name == "Products"


@pytest.mark.asyncio
async def test_get_category_not_found(mock_writer, mock_categories_response):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(return_value=mock_categories_response)

    category = await writer.get_category("nonexistent_id")

    assert category is None


@pytest.mark.asyncio
async def test_get_category_failure(mock_writer):
    writer, mock_client = mock_writer
    mock_client.request = AsyncMock(side_effect=Exception("API Error"))

    category = await writer.get_category("some_id")

    assert category is None


# ─────────────────────────────────────────────
# Cascade delete: group expense + its expenses
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_group_expense_cascades_related_expenses(mock_writer, mock_group_expenses_response):
    """
    Simulates the handler logic: when deleting a group expense,
    all related personal expenses should also be deleted.
    """
    writer, mock_client = mock_writer

    page_data = mock_group_expenses_response["results"][0]
    page_data["properties"]["Expenses"] = {
        "relation": [{"id": "uuid_expense_1"}, {"id": "uuid_expense_2"}]
    }
    mock_client.pages.retrieve = AsyncMock(return_value=page_data)
    mock_client.pages.update = AsyncMock(return_value={})

    group_expenses = await writer.get_group_expenses(["uuid_grexpense_1"])
    assert len(group_expenses) == 1
    related_ids = group_expenses[0].expenses_relations
    assert len(related_ids) == 2

    # Simulate cascade delete (as the handler does)
    for exp_id in related_ids:
        await writer.delete_page(exp_id)
    await writer.delete_page("uuid_grexpense_1")

    # delete_page (pages.update archived=True) should be called 3 times total
    assert mock_client.pages.update.call_count == 3
    calls = [c.kwargs["page_id"] for c in mock_client.pages.update.call_args_list]
    assert "uuid_expense_1" in calls
    assert "uuid_expense_2" in calls
    assert "uuid_grexpense_1" in calls
