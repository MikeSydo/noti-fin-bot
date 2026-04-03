import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from models.expense import Expense
from models.category import Category
from models.account import Account
from datetime import datetime
from services.analytics import calculate_statistics, analyze_budget_exceeded, compare_periods

@pytest.fixture
def mock_categories():
    return [
        Category(id="cat_1", name="Food", monthly_budget=Decimal("500")),
        Category(id="cat_2", name="Transport", monthly_budget=Decimal("100")),
        Category(id="cat_3", name="Entertainment", monthly_budget=None),
    ]

@pytest.fixture
def mock_expenses(mock_categories):
    acc = Account(id="acc_1", name="Cash")
    return [
        Expense(name="Lunch", amount=Decimal("150"), date=datetime.now(), account=acc, category=mock_categories[0]),
        Expense(name="Groceries", amount=Decimal("400"), date=datetime.now(), account=acc, category=mock_categories[0]),
        Expense(name="Bus", amount=Decimal("50"), date=datetime.now(), account=acc, category=mock_categories[1]),
        Expense(name="Movies", amount=Decimal("200"), date=datetime.now(), account=acc, category=mock_categories[2]),
        Expense(name="Unknown Thing", amount=Decimal("100"), date=datetime.now(), account=acc, category=None),
    ]

def test_calculate_statistics(mock_expenses, mock_categories):
    stats, total, overbudget = calculate_statistics(mock_expenses, mock_categories)

    assert total == Decimal("900")  # 150 + 400 + 50 + 200 + 100

    cat1_stats = stats["cat_1"]
    assert cat1_stats["amount"] == Decimal("550")
    assert cat1_stats["tx_count"] == 2
    assert cat1_stats["max_budget"] == Decimal("500")
    assert cat1_stats["percent_of_total"] == (Decimal("550") / Decimal("900")) * 100
    assert cat1_stats["percent_of_budget"] == (Decimal("550") / Decimal("500")) * 100

    cat3_stats = stats["cat_3"]
    assert cat3_stats["amount"] == Decimal("200")
    assert cat3_stats["max_budget"] is None
    assert cat3_stats["percent_of_budget"] == Decimal("0")

    unknown_stats = stats["unknown"]
    assert unknown_stats["amount"] == Decimal("100")
    assert unknown_stats["name"] == "Без категорії"

    # Check overbudget
    assert len(overbudget) == 1
    assert overbudget[0]["name"] == "Food"
    assert overbudget[0]["excess"] == Decimal("50")

@pytest.mark.asyncio
@patch("services.analytics.client")
async def test_analyze_budget_exceeded_success(mock_client):
    mock_response = MagicMock()
    mock_response.text = "Ось рекомендації українською: не їсти стільки хліба."
    mock_client.models.generate_content.return_value = mock_response

    result = await analyze_budget_exceeded("Food: 50 excess")
    assert "рекомендації українською" in result

    mock_client.models.generate_content.assert_called_once()
    called_args = mock_client.models.generate_content.call_args.kwargs
    assert "Analyze the following expense categories" in called_args["contents"]
    assert "in Ukrainian" in called_args["contents"]

@pytest.mark.asyncio
@patch("services.analytics.client")
async def test_analyze_budget_exceeded_failure(mock_client):
    mock_client.models.generate_content.side_effect = Exception("Network Error")

    result = await analyze_budget_exceeded("Food: 50 excess")
    assert result == "Не вдалося отримати рекомендації від AI."

@pytest.mark.asyncio
@patch("services.analytics.client")
async def test_compare_periods_success(mock_client):
    mock_response = MagicMock()
    mock_response.text = "Аналіз: витрати зросли."
    mock_client.models.generate_content.return_value = mock_response

    result = await compare_periods("Current: 500", "Prev: 300")
    assert result == "Аналіз: витрати зросли."

    mock_client.models.generate_content.assert_called_once()
    called_args = mock_client.models.generate_content.call_args.kwargs
    assert "Compare expenses for two periods" in called_args["contents"]
    assert "in Ukrainian" in called_args["contents"]

@pytest.mark.asyncio
@patch("services.analytics.client")
async def test_compare_periods_failure(mock_client):
    mock_client.models.generate_content.side_effect = Exception("Network Error")

    result = await compare_periods("Current: 500", "Prev: 300")
    assert result == "Не вдалося отримати аналіз від AI."
