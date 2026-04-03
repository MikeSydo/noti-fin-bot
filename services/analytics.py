from decimal import Decimal
from typing import List, Dict, Any, Tuple
import logging
from config import settings
from google import genai
from models.expense import Expense
from models.category import Category

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GEMINI_API_KEY)

def calculate_statistics(expenses: List[Expense], categories: List[Category]) -> Tuple[Dict[str, Any], Decimal, List[Dict[str, Any]]]:
    """
    Calculates statistics: Total sum, sum per category, % of total, % of max budget, tx count.
    Also returns a list of overbudget categories.
    """
    total_amount = Decimal('0')
    category_stats: Dict[str, Dict[str, Any]] = {}

    # Init dictionary with all available categories
    for cat in categories:
        category_stats[cat.id or "unknown"] = {
            "name": cat.name,
            "amount": Decimal('0'),
            "tx_count": 0,
            "max_budget": cat.monthly_budget,
            "percent_of_total": Decimal('0'),
            "percent_of_budget": Decimal('0'),
        }

    for exp in expenses:
        total_amount += exp.amount
        cat_id = exp.category.id if exp.category else "unknown"

        if cat_id not in category_stats:
             category_stats[cat_id] = {
                "name": exp.category.name if exp.category else "Без категорії",
                "amount": Decimal('0'),
                "tx_count": 0,
                "max_budget": None,
                "percent_of_total": Decimal('0'),
                "percent_of_budget": Decimal('0'),
            }

        category_stats[cat_id]["amount"] += exp.amount
        category_stats[cat_id]["tx_count"] += 1

    overbudget_categories = []

    for cat_id, stats in category_stats.items():
        if total_amount > 0:
            stats["percent_of_total"] = (stats["amount"] / total_amount) * 100

        if stats["max_budget"] is not None and stats["max_budget"] > 0:
            stats["percent_of_budget"] = (stats["amount"] / stats["max_budget"]) * 100

            if stats["amount"] > stats["max_budget"]:
                overbudget_categories.append({
                    "name": stats["name"],
                    "spent": stats["amount"],
                    "limit": stats["max_budget"],
                    "excess": stats["amount"] - stats["max_budget"]
                })

    return category_stats, total_amount, overbudget_categories

async def analyze_budget_exceeded(overbudget_data: str) -> str:
    """
    Query Gemini for recommendations on overbudget categories.
    """
    prompt = f"""
        Analyze the following expense categories where the budget was exceeded:
        {overbudget_data}
        Give short, friendly, and practical recommendations in Ukrainian on how to 
        optimize these expenses or avoid buying non-essential items.
        Do not use markdown formatting, just plain text.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text

    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return "🤖 Перевищено безкоштовний ліміт запитів до AI. Будь ласка, зачекайте хвилину і спробуйте знову."
        return "Не вдалося отримати рекомендації від AI."

async def compare_periods(current_period_data: str, previous_period_data: str) -> str:
    """
    Query Gemini to compare two periods of expenses.
    """
    prompt = f"""
        Compare expenses for two periods:
        Current period:
        {current_period_data}
        Previous period:
        {previous_period_data}
        Provide a brief analysis in Ukrainian: whether expenses increased, in which categories the largest differences are, 
        and give a general verdict on financial behavior. Do not use markdown formatting, just plain text.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text

    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return "🤖 Перевищено безкоштовний ліміт запитів до AI. Будь ласка, зачекайте хвилину і спробуйте знову."
        return "Не вдалося отримати аналіз від AI."