from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
from app.keyboards.reply import get_analytics_menu, get_main_menu
from services.notion_writer import NotionWriter
from services.analytics import calculate_statistics, generate_yearly_budget_graph, generate_trend_graph
from services.i18n import i18n
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from decimal import Decimal
from app.keyboards.inline import get_accounts_keyboard, get_years_inline_keyboard, get_months_inline_keyboard

router = Router()

class AnalyticsState(StatesGroup):
    waiting_for_report_type = State()
    waiting_for_account_stats = State()
    waiting_for_account_trend = State()
    waiting_for_year_stats = State()
    waiting_for_year_trend = State()
    waiting_for_month_trend = State()

@router.message(F.text.in_(i18n.get_all_translations('btn_analytics')))
async def analytics_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer(
        i18n.get_text('rep_choose_type', user_id), 
        reply_markup=await get_analytics_menu(user_id)
    )

    await state.set_state(AnalyticsState.waiting_for_report_type)

@router.message(AnalyticsState.waiting_for_report_type, F.text.in_(i18n.get_all_translations('menu_analytics_main_menu')))
async def exit_analytics(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await message.answer(i18n.get_text('msg_main_menu', user_id), reply_markup=await get_main_menu(user_id))

@router.message(AnalyticsState.waiting_for_report_type, F.text.in_(i18n.get_all_translations('menu_stats')))
async def process_stats_type(message: Message, state: FSMContext):
    user_id = message.from_user.id
    writer = NotionWriter()
    accounts = await writer.get_accounts()

    markup = await get_accounts_keyboard(accounts, include_skip=False, user_id=user_id)
    await message.answer(i18n.get_text('rep_choose_account_stats', user_id), reply_markup=markup)
    await state.set_state(AnalyticsState.waiting_for_account_stats)

@router.message(AnalyticsState.waiting_for_report_type, F.text.in_(i18n.get_all_translations('menu_comparison')))
async def process_comp_type(message: Message, state: FSMContext):
    user_id = message.from_user.id
    writer = NotionWriter()
    accounts = await writer.get_accounts()

    markup = await get_accounts_keyboard(accounts, include_skip=False, user_id=user_id)
    await message.answer(i18n.get_text('rep_choose_account_trend', user_id), reply_markup=markup)
    await state.set_state(AnalyticsState.waiting_for_account_trend)

@router.callback_query(AnalyticsState.waiting_for_account_stats, F.data.startswith('select_account_'))
async def process_account_stats(callback: CallbackQuery, state: FSMContext):
    account_id = callback.data.split('select_account_')[-1]
    await state.update_data(account_id=account_id)

    writer = NotionWriter()
    expenses = await writer.get_all_expenses()
    account_expenses = [exp for exp in expenses if exp.account and exp.account.id == account_id]

    years = sorted(list(set([exp.date.year for exp in account_expenses]))) if account_expenses else [datetime.now().year]

    user_id = callback.from_user.id
    markup = await get_years_inline_keyboard(years, 'year_stats', user_id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        i18n.get_text('rep_choose_year', user_id),
        reply_markup=markup
    )
    await state.set_state(AnalyticsState.waiting_for_year_stats)
    await callback.answer()

@router.callback_query(AnalyticsState.waiting_for_account_trend, F.data.startswith('select_account_'))
async def process_account_trend(callback: CallbackQuery, state: FSMContext):
    account_id = callback.data.split('select_account_')[-1]
    await state.update_data(account_id=account_id)

    writer = NotionWriter()
    expenses = await writer.get_all_expenses()
    account_expenses = [exp for exp in expenses if exp.account and exp.account.id == account_id]

    years = sorted(list(set([exp.date.year for exp in account_expenses]))) if account_expenses else [datetime.now().year]

    user_id = callback.from_user.id
    markup = await get_years_inline_keyboard(years, 'year_trend', user_id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        i18n.get_text('rep_choose_year', user_id),
        reply_markup=markup
    )
    await state.set_state(AnalyticsState.waiting_for_year_trend)
    await callback.answer()

# Cancel comp was bound to waiting_for_dates_trend, just keeping general cancel via menu
@router.message(AnalyticsState.waiting_for_year_trend, F.text.in_(i18n.get_all_translations('menu_cancel')))
async def cancel_comp(message: Message, state: FSMContext):
    await analytics_start(message, state)

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str.strip(), "%d.%m.%Y")

@router.callback_query(AnalyticsState.waiting_for_year_stats, F.data.startswith('year_stats_'))
async def process_year_stats(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    year = int(callback.data.split('_')[-1])

    await callback.message.edit_reply_markup(reply_markup=None)
    msg = await callback.message.answer(i18n.get_text('rep_gathering_data', user_id))

    user_data = await state.get_data()
    account_id = user_data.get('account_id')

    writer = NotionWriter()
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    expenses = await writer.get_expenses_by_date_range(start_date, end_date)

    if account_id:
        expenses = [e for e in expenses if e.account and e.account.id == account_id]

    if not expenses:
        await msg.answer(i18n.get_text('rep_no_expenses', user_id))
        await state.clear()
        return

    # Use monthly budget from the selected account
    monthly_budget = Decimal('10000')
    account_name = i18n.get_text('txt_all', user_id)
    if account_id:
        selected_account = await writer.get_account(account_id)
        if selected_account:
            account_name = selected_account.name
            if selected_account.monthly_budget:
                monthly_budget = selected_account.monthly_budget

    photo_buf = generate_yearly_budget_graph(expenses, year, monthly_budget, user_id)
    photo = BufferedInputFile(photo_buf.getvalue(), filename=f"stats_{year}.png")

    caption = i18n.get_text('rep_stats_caption', user_id, year=year, account_name=account_name)
    await msg.answer_photo(photo=photo, caption=caption)

    # Calculate and send textual statistics
    categories = await writer.get_categories()
    category_stats, total_amount, _ = calculate_statistics(expenses, categories, user_id)

    stats_text = i18n.get_text('rep_stats_text_header', user_id, year=year, account_name=account_name, total_amount=f"{total_amount:.2f}")

    sorted_stats = sorted(category_stats.values(), key=lambda x: x['amount'], reverse=True)
    for stat in sorted_stats:
        if stat['amount'] > 0:
            stats_text += f"• {stat['name']}: {stat['amount']:.2f} ({stat['percent_of_total']:.1f}%)\n"

    if total_amount > 0:
        await msg.answer(stats_text, parse_mode="Markdown")

    await state.clear()
    await msg.answer(i18n.get_text('msg_main_menu', user_id), reply_markup=await get_main_menu(user_id))
    await callback.answer()

@router.callback_query(AnalyticsState.waiting_for_year_trend, F.data.startswith('year_trend_'))
async def process_year_trend(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    year = int(callback.data.split('_')[-1])
    await state.update_data(trend_year=year)

    markup = await get_months_inline_keyboard('month_trend', user_id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        i18n.get_text('rep_choose_month', user_id),
        reply_markup=markup
    )
    await state.set_state(AnalyticsState.waiting_for_month_trend)
    await callback.answer()


@router.callback_query(AnalyticsState.waiting_for_month_trend, F.data.startswith('month_trend_'))
async def process_trend_month(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    month = int(callback.data.split('_')[-1])

    await callback.message.edit_reply_markup(reply_markup=None)
    msg = await callback.message.answer(i18n.get_text('rep_gathering_data', user_id))

    user_data = await state.get_data()
    account_id = user_data.get('account_id')
    year = user_data.get('trend_year', datetime.now().year)

    writer = NotionWriter()
    # To optimize memory usage, let's fetch only specific range
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year, 12, 31, 23, 59, 59)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

    expenses = await writer.get_expenses_by_date_range(start_date, end_date)

    if account_id:
        expenses = [e for e in expenses if e.account and e.account.id == account_id]

    if not expenses:
        await msg.answer(i18n.get_text('rep_no_expenses', user_id))
        await state.clear()
        await callback.answer()
        return

    photo_buf = generate_trend_graph(expenses, year, month, user_id)
    photo = BufferedInputFile(photo_buf.getvalue(), filename="trend.png")

    caption = i18n.get_text('rep_trend_caption', user_id)
    await msg.answer_photo(photo=photo, caption=caption)

    await state.clear()
    await msg.answer(i18n.get_text('msg_main_menu', user_id), reply_markup=await get_main_menu(user_id))
    await callback.answer()
