from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
from app.keyboards.reply import get_analytics_menu, get_comparison_periods_menu, get_main_menu
from services.notion_writer import NotionWriter
from services.analytics import calculate_statistics, analyze_budget_exceeded, compare_periods

router = Router()

class AnalyticsState(StatesGroup):
    waiting_for_report_type = State()
    waiting_for_dates_stats = State()
    waiting_for_period_comp = State()

@router.message(F.text == 'Аналітика')
async def analytics_start(message: Message, state: FSMContext):
    await message.answer(
        "Оберіть тип аналітики:", 
        reply_markup=await get_analytics_menu()
    )

    await state.set_state(AnalyticsState.waiting_for_report_type)

@router.message(AnalyticsState.waiting_for_report_type, F.text == '⬅️ Головне меню')
async def exit_analytics(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Головне меню", reply_markup=await get_main_menu())

@router.message(AnalyticsState.waiting_for_report_type, F.text == '📊 Статистика')
async def process_stats_type(message: Message, state: FSMContext):
    await message.answer(
        "Введіть дату (наприклад 1.10.2023) або діапазон дат (наприклад 1.10.2023 - 15.10.2023):"
    )

    await state.set_state(AnalyticsState.waiting_for_dates_stats)

@router.message(AnalyticsState.waiting_for_report_type, F.text == '⚖️ Порівняння')
async def process_comp_type(message: Message, state: FSMContext):
    await message.answer("Оберіть період для порівняння:", reply_markup=await get_comparison_periods_menu())
    await state.set_state(AnalyticsState.waiting_for_period_comp)

@router.message(AnalyticsState.waiting_for_period_comp, F.text == '⬅️ Скасувати')
async def cancel_comp(message: Message, state: FSMContext):
    await analytics_start(message, state)

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str.strip(), "%d.%m.%Y")

@router.message(AnalyticsState.waiting_for_dates_stats)
async def process_stats_dates(message: Message, state: FSMContext):
    text = message.text or ""

    try:
        if "-" in text:
            start_str, end_str = text.split("-")
            start_date = parse_date(start_str)
            end_date = parse_date(end_str)
        else:
            start_date = parse_date(text)
            end_date = start_date

    except ValueError:
        await message.answer("Неправильний формат дати. Спробуйте ще раз (наприклад, 1.10.2023 або 1.10.2023 - 15.10.2023)")
        return

    await message.answer("Збираю дані. Зачекайте...")

    writer = NotionWriter()
    categories = await writer.get_categories()
    expenses = await writer.get_expenses_by_date_range(start_date, end_date)

    if not expenses:
        await message.answer("Не знайдено витрат за цей період.")
        await state.clear()
        return

    stats, total, overbudget = calculate_statistics(expenses, categories)
    report = f"📊 *Статистика витрат*\nЗагалом витрачено: {total}\n\n"

    for cat_id, data in stats.items():
        if data["tx_count"] > 0:
            report += f"🔹 {data['name']}: {data['amount']} ({data['percent_of_total']:.1f}% від усіх)"
            if data["max_budget"]:
                report += f" | {data['percent_of_budget']:.1f}% від ліміту"
            report += "\n"

    if overbudget:
        overbudget_info = "\n".join(
            [f"{item['name']}: витрачено {item['spent']}, ліміт {item['limit']}, перевищено на {item['excess']}" for item in overbudget]
        )

        await message.answer("Аналізую перевищення бюджету через AI...")
        ai_advice = await analyze_budget_exceeded(overbudget_info)
        report += "\n🤖 *Поради від AI:*\n" + ai_advice

    # Send long reports gracefully
    for i in range(0, len(report), 4000):
        await message.answer(report[i:i+4000], parse_mode="Markdown")

    await state.clear()
    await message.answer("Головне меню", reply_markup=await get_main_menu())

@router.message(AnalyticsState.waiting_for_period_comp)
async def process_comp_period(message: Message, state: FSMContext):
    period = message.text
    now = datetime.now()

    if period == 'Цей день':
        current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        current_end = current_start
        prev_start = current_start - timedelta(days=1)
        prev_end = prev_start

    elif period == 'Цей тиждень':
        current_start = now - timedelta(days=now.weekday())
        current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
        current_end = now
        prev_start = current_start - timedelta(days=7)
        prev_end = current_start - timedelta(days=1)

    elif period == 'Цей місяць':
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = now
        # simple previous month logic
        first_day_prev = (current_start - timedelta(days=1)).replace(day=1)
        prev_start = first_day_prev
        prev_end = current_start - timedelta(days=1)
    else:
        await message.answer("Оберіть період із клавіатури.")
        return

    await message.answer("Збираю дані. Зачекайте...")

    writer = NotionWriter()
    categories = await writer.get_categories()
    curr_exp = await writer.get_expenses_by_date_range(current_start, current_end)
    prev_exp = await writer.get_expenses_by_date_range(prev_start, prev_end)

    curr_stats, curr_total, _ = calculate_statistics(curr_exp, categories)
    prev_stats, prev_total, _ = calculate_statistics(prev_exp, categories)

    def format_stats(stats, total):
        res = f"Загальна сума: {total}\n"
        for _, data in stats.items():
            if data["tx_count"] > 0:
                res += f"- {data['name']}: {data['amount']}\n"
        return res

    curr_data_str = format_stats(curr_stats, curr_total)
    prev_data_str = format_stats(prev_stats, prev_total)
    await message.answer("Аналізую порівняння через AI...")

    ai_verdict = await compare_periods(curr_data_str, prev_data_str)
    report = f"⚖️ *Порівняння:* {period}\n\n🤖 *Вердикт від AI:*\n{ai_verdict}"

    # Send long reports gracefully
    for i in range(0, len(report), 4000):
        await message.answer(report[i:i+4000], parse_mode="Markdown")

    await state.clear()
    await message.answer("Головне меню", reply_markup=await get_main_menu())