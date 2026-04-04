from decimal import Decimal
from typing import List, Dict, Any, Tuple
from models.expense import Expense
from models.category import Category
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import pandas as pd
from datetime import date
from services.i18n import i18n

def calculate_statistics(expenses: List[Expense], categories: List[Category], user_id: int) -> Tuple[Dict[str, Any], Decimal, List[Dict[str, Any]]]:
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
                "name": exp.category.name if exp.category else i18n.get_text('txt_no_category', user_id),
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

def generate_yearly_budget_graph(expenses: List[Expense], year: int, monthly_budget: Decimal, user_id: int) -> io.BytesIO:
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
    ax.bar(months, totals, color=colors, label=i18n.get_text('graph_expenses_label', user_id))

    ax.axhline(y=budget, color='blue', linestyle='--', label=i18n.get_text('graph_budget_label', user_id))

    ax.set_xticks(months)
    ax.set_xticklabels(i18n.get_text('graph_months', user_id))
    ax.set_ylabel(i18n.get_text('graph_y_label', user_id))
    ax.set_title(i18n.get_text('graph_title', user_id, year=year))
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_trend_graph(expenses: List[Expense], year: int, month: int, user_id: int) -> io.BytesIO:
    """
    Generates a scatter plot of items purchased within a specific month.
    X-axis: count of purchases, Y-axis: total amount spent on that item.
    """
    df = pd.DataFrame([
        {'name': exp.name.strip(), 'amount': float(exp.amount)}
        for exp in expenses if exp.date.year == year and exp.date.month == month
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

    group_df = df.groupby('name').agg(
        count=('name', 'size'),
        total=('amount', 'sum')
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(group_df['count'], group_df['total'], color='blue', alpha=0.7)

    # Annotate points with item names
    for i, row in group_df.iterrows():
        ax.annotate(row['name'], (row['count'], row['total']), xytext=(5, 5), textcoords='offset points')

    ax.set_xlabel(i18n.get_text('graph_trend_x', user_id))
    ax.set_ylabel(i18n.get_text('graph_trend_y', user_id))
    
    # Ensure x-axis only shows integers, and sets standard max of at least 5
    max_count = max(group_df['count'].max(), 5)
    ax.set_xticks(range(1, max_count + 1))
    
    month_name = i18n.get_text('graph_months', user_id)[month - 1]
    ax.set_title(i18n.get_text('graph_trend_title', user_id, month_name=month_name, year=year))


    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf
