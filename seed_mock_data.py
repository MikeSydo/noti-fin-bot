import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal

from services.notion_writer import NotionWriter
from models.category import Category
from models.expense import Expense

async def seed_data():
    writer = NotionWriter()

    print("Getting accounts...")
    accounts = await writer.get_accounts()
    if not accounts:
        print("Please create accounts first via Telegram or Notion.")
        return

    print(f"Found {len(accounts)} accounts:")
    for a in accounts:
        print(f" - {a.name} (Budget: {a.monthly_budget})")

    print("Fetching categories...")
    existing_cats = await writer.get_categories()
    existing_cat_names = [c.name for c in existing_cats]

    cat_defs = {
        "Продукти": ["Молоко", "Хліб", "М'ясо", "Сільпо", "АТБ", "Свіжі овочі", "Фрукти"],
        "Транспорт": ["Метро", "Таксі Uklon", "Таксі Bolt", "Бензин", "Квиток на потяг", "Ремонт авто"],
        "Розваги": ["Кінотеатр", "Кафе", "Ресторан", "Підписка Netflix", "Бар", "Більярд"],
        "Житло": ["Оренда", "Комуналка", "Інтернет", "Прибирання", "Ремонт"],
        "Здоров'я": ["Аптека", "Лікар", "Стоматолог", "Вітаміни"],
        "Шопінг": ["Одяг", "Взуття", "Косметика", "Подарунок", "Курси"]
    }

    categories = []

    for cname in cat_defs.keys():
        if cname not in existing_cat_names:
            print(f"Creating category: {cname}")
            new_cat = Category(name=cname)
            resp = await writer.client.pages.create(
                parent={"database_id": writer.categories_db_id},
                properties=new_cat.to_notion_properties()
            )
            categories.append(Category(id=resp["id"], name=cname))
        else:
            categories.append(next(c for c in existing_cats if c.name == cname))

    print(f"Categories ready: {len(categories)}")

    expenses_to_create = 250
    print(f"Generating {expenses_to_create} expenses from early 2025 until today...")

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 4, 4)
    delta = end_date - start_date

    # Sort so that Notion creates them dynamically
    expenses = []

    for i in range(expenses_to_create):
        # Pick random date
        random_days = random.randint(0, delta.days)
        exp_date = start_date + timedelta(days=random_days)
        exp_date = exp_date.replace(hour=random.randint(8, 22), minute=random.randint(0, 59))

        account = random.choice(accounts)
        category = random.choice(categories)
        name = random.choice(cat_defs[category.name])

        # Determine amount range based on category
        if category.name == "Житло":
            amount = Decimal(str(random.randint(1000, 15000)))
        elif category.name == "Продукти":
            amount = Decimal(str(random.randint(200, 2000)))
        elif category.name == "Транспорт":
            amount = Decimal(str(random.randint(50, 1500)))
        else:
            amount = Decimal(str(random.randint(100, 5000)))

        amount += Decimal(str(random.randint(0, 99))) / Decimal('100')

        expense = Expense(
            name=name,
            amount=amount,
            date=exp_date.isoformat(),
            account=account,
            category=category
        )
        expenses.append((expense, exp_date))

    # sort expenses roughly by date, wait actually it doesn't matter since we specify the 'date' property.
    expenses.sort(key=lambda x: x[1])

    # We should run them synchronously to avoid rate limiting
    # Rate limit: max 3 per second

    for i, (expense, dt) in enumerate(expenses):
        print(f"[{i+1}/{expenses_to_create}] Creating expense: {expense.name} - {expense.amount} at {dt.strftime('%Y-%m-%d')}")
        await writer.add_expense(expense)
        await asyncio.sleep(0.35) # To be safe with Notion API rate limits (1 / 0.35 = ~2.8 requests per second)

    print("Done generating mock data!")

if __name__ == '__main__':
    asyncio.run(seed_data())
