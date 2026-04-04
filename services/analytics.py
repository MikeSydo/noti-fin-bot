from decimal import Decimal
from typing import List, Dict, Any, Tuple
import logging
from config import settings
from google import genai
from models.expense import Expense
from models.category import Category
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import pandas as pd
from datetime import date

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
            "max_budget": None,
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

def generate_yearly_budget_graph(expenses: List[Expense], year: int, monthly_budget: Decimal) -> io.BytesIO:
    """
    Generates a bar chart showing exact expenses per month compared to the monthly budget.
    """
    monthly_totals = {i: Decimal('0') for i in range(1, 13)}

    for exp in expenses:
        if exp.date.year == year:
            monthly_totals[exp.date.month] += exp.amount

    months = list(range(1, 13))
    totals = [float(monthly_totals[m]) for m in months]
    budget = float(monthly_budget)

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['red' if t > budget else 'green' for t in totals]
    bars = ax.bar(months, totals, color=colors, label='Витрати')

    ax.axhline(y=budget, color='blue', linestyle='--', label='Місячний бюджет')

    ax.set_xticks(months)
    ax.set_xticklabels(['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер', 'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру'])
    ax.set_ylabel('Сума')
    ax.set_title(f'Річний звіт за {year} рік')
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_trend_graph(expenses: List[Expense], start_date: date, end_date: date) -> io.BytesIO:
    """
    Generates an expense trend line chart, with forecasting.
    Scales to months if range is > 2 months, otherwise uses days.
    """
    delta = (end_date - start_date).days

    df = pd.DataFrame([
        {'date': exp.date.date(), 'amount': float(exp.amount)}
        for exp in expenses if start_date <= exp.date.date() <= end_date
    ])

    if df.empty:
        # Return empty plot if no data
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'Немає даних за цей період', horizontalalignment='center', verticalalignment='center')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return buf

    df['date'] = pd.to_datetime(df['date'])

    is_monthly = delta > 60
    freq_str = 'ME' if is_monthly else 'D'
    group_df = df.groupby(pd.Grouper(key='date', freq=freq_str))['amount'].sum().reset_index()

    # Simple linear prediction
    x = np.arange(len(group_df))
    y = group_df['amount'].values

    if len(x) > 1:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)

        # Predict next periods (same amount as historical)
        future_x = np.arange(len(x), len(x) * 2)
        future_y = p(future_x)

        # Generate future dates
        last_date = group_df['date'].max()
        if is_monthly:
            future_dates = [last_date + pd.DateOffset(months=i) for i in range(1, len(future_x) + 1)]
        else:
            future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, len(future_x) + 1)]
    else:
        future_x = []
        future_y = []
        future_dates = []

    fig, ax = plt.subplots(figsize=(10, 6))

    width = 20 if is_monthly else 0.8
    ax.bar(group_df['date'], group_df['amount'], width=width, color='blue', alpha=0.7, label='Фактичні витрати')

    if len(future_x) > 0:
        ax.plot(future_dates, future_y, linestyle='--', color='orange', marker='x', linewidth=2, label='Прогноз тенденції')

    if is_monthly:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    fig.autofmt_xdate()

    ax.set_ylabel('Сума')
    ax.set_title('Тенденція витрат та прогноз')
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf
