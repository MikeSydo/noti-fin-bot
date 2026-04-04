import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from models.expense import Expense
from models.category import Category
from models.account import Account
from datetime import datetime
from services.analytics import calculate_statistics

@pytest.fixture
def mock_categories():
    return [
        Category(id="cat_1", name="Food"),
        Category(id="cat_2", name="Transport"),
        Category(id="cat_3", name="Entertainment"),
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
    stats, total, overbudget = calculate_statistics(mock_expenses, mock_categories, user_id=1)

    assert total == Decimal("900")  # 150 + 400 + 50 + 200 + 100

    cat1_stats = stats["cat_1"]
    assert cat1_stats["amount"] == Decimal("550")
    assert cat1_stats["tx_count"] == 2
    assert cat1_stats["max_budget"] is None
    assert cat1_stats["percent_of_total"] == (Decimal("550") / Decimal("900")) * 100
    assert cat1_stats["percent_of_budget"] == Decimal("0")

    cat3_stats = stats["cat_3"]
    assert cat3_stats["amount"] == Decimal("200")
    assert cat3_stats["max_budget"] is None
    assert cat3_stats["percent_of_budget"] == Decimal("0")

    unknown_stats = stats["unknown"]
    assert unknown_stats["amount"] == Decimal("100")
    assert unknown_stats["name"] == "Без категорії"

    # Check overbudget
    assert len(overbudget) == 0

#Removed old analyze_budget_exceeded and compare_periods tests since these functions were superseded by graphical implementations
