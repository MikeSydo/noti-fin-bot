import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dateutil.relativedelta import relativedelta
import os

from services.i18n import i18n
from services.notion_writer import NotionWriter
from services.analytics import generate_category_pie_chart, generate_weekly_bar_chart, generate_comparison_bar_chart
from app.keyboards.reply import get_main_menu, get_analytics_menu, get_comparison_periods_menu
from app.keyboards.inline import get_months_inline_keyboard, get_years_inline_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Directory to temporarily store generated charts
REPORTS_DIR = "reports_temp"
os.makedirs(REPORTS_DIR, exist_ok=True)


class AnalyticsState(StatesGroup):
    waiting_for_menu_selection = State()
    waiting_for_month_selection = State()
    waiting_for_comparison_period_selection = State()


@router.message(F.text.in_(i18n.get_all_translations('btn_analytics')))
async def start_analytics(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Entry point for Analytics."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('msg_analytics_menu', user_id),
        reply_markup=await get_analytics_menu(user_id)
    )
    await state.set_state(AnalyticsState.waiting_for_menu_selection)


@router.message(F.text.in_(i18n.get_all_translations('menu_analytics_main_menu')))
async def back_to_main_menu(message: Message, state: FSMContext):
    """Return to the main menu."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('msg_main_menu', user_id),
        reply_markup=await get_main_menu(user_id)
    )


@router.message(F.text.in_(i18n.get_all_translations('menu_stats')), AnalyticsState.waiting_for_menu_selection)
async def prompt_for_stats_month(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Prompt user to select a month for the category breakdown."""
    user_id = message.from_user.id
    current_year = datetime.now().year
    
    # We'll offer a choice: select a month for the current year.
    # To keep it simple, we just show 12 months.
    await message.answer(
        i18n.get_text('msg_select_month', user_id),
        reply_markup=await get_months_inline_keyboard(prefix="stats_month", user_id=user_id)
    )
    await state.set_state(AnalyticsState.waiting_for_month_selection)


@router.callback_query(F.data.startswith('stats_month_'), AnalyticsState.waiting_for_month_selection)
async def generate_monthly_stats(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Process month selection and generate category pie chart and weekly bar chart."""
    user_id = callback.from_user.id
    await callback.answer()
    
    month = int(callback.data.split('_')[2])
    year = datetime.now().year
    
    # Send processing message
    processing_msg = await callback.message.answer(i18n.get_text('msg_generating_report', user_id))
    
    # Calculate date range
    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)
    
    try:
        # Get expenses for the month
        expenses = await notion_writer.get_expenses_by_date_range(start_date, end_date)
        
        if not expenses:
            await processing_msg.edit_text(i18n.get_text('msg_no_data_for_period', user_id))
            return
            
        # Generate Category Pie Chart
        month_name = i18n.get_text('graph_months', user_id)[month-1]
        pie_chart_path = os.path.join(REPORTS_DIR, f"pie_{user_id}_{year}_{month}.png")
        generate_category_pie_chart(expenses, i18n.get_text('graph_category_breakdown', user_id, month=month_name), pie_chart_path)
        
        # Generate Weekly Bar Chart
        bar_chart_path = os.path.join(REPORTS_DIR, f"bar_{user_id}_{year}_{month}.png")
        generate_weekly_bar_chart(expenses, year, month, i18n.get_text('graph_weekly_spending', user_id, month=month_name), bar_chart_path)
        
        # Send charts
        from aiogram.types import InputMediaPhoto
        media = [
            InputMediaPhoto(media=FSInputFile(pie_chart_path), caption=i18n.get_text('msg_stats_caption', user_id, month=month_name)),
            InputMediaPhoto(media=FSInputFile(bar_chart_path))
        ]
        
        await callback.message.answer_media_group(media=media)
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error generating monthly stats: {e}")
        await processing_msg.edit_text(i18n.get_text('msg_report_error', user_id))
        
    finally:
        # State stays waiting_for_month_selection so they can pick another month if they want,
        # or they can use the reply keyboard to go back to main menu.
        pass


@router.message(F.text.in_(i18n.get_all_translations('menu_comparison')), AnalyticsState.waiting_for_menu_selection)
async def prompt_for_comparison_period(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Prompt user to select a period for comparison (Today vs Yesterday, This Week vs Last Week, This Month vs Last Month)."""
    user_id = message.from_user.id
    
    await message.answer(
        i18n.get_text('msg_select_comparison_period', user_id),
        reply_markup=await get_comparison_periods_menu(user_id)
    )
    await state.set_state(AnalyticsState.waiting_for_comparison_period_selection)


@router.message(F.text.in_(i18n.get_all_translations('menu_today')), AnalyticsState.waiting_for_comparison_period_selection)
async def compare_today(message: Message, state: FSMContext, notion_writer: NotionWriter):
    user_id = message.from_user.id
    now = datetime.now()
    
    current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    current_end = now
    
    previous_start = current_start - relativedelta(days=1)
    previous_end = previous_start.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

    await process_comparison(
        message, 
        current_start, current_end, 
        previous_start, previous_end,
        i18n.get_text('label_today', user_id), 
        i18n.get_text('label_yesterday', user_id),
        user_id,
        notion_writer
    )


@router.message(F.text.in_(i18n.get_all_translations('menu_this_week')), AnalyticsState.waiting_for_comparison_period_selection)
async def compare_this_week(message: Message, state: FSMContext, notion_writer: NotionWriter):
    user_id = message.from_user.id
    now = datetime.now()
    
    # Assuming week starts on Monday
    current_start = (now - relativedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    current_end = now
    
    previous_start = current_start - relativedelta(weeks=1)
    previous_end = now - relativedelta(weeks=1)

    await process_comparison(
        message, 
        current_start, current_end, 
        previous_start, previous_end,
        i18n.get_text('label_this_week', user_id), 
        i18n.get_text('label_last_week', user_id),
        user_id,
        notion_writer
    )


@router.message(F.text.in_(i18n.get_all_translations('menu_this_month')), AnalyticsState.waiting_for_comparison_period_selection)
async def compare_this_month(message: Message, state: FSMContext, notion_writer: NotionWriter):
    user_id = message.from_user.id
    now = datetime.now()
    
    current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_end = now
    
    previous_start = current_start - relativedelta(months=1)
    # Calculate equivalent point in previous month. Handle edge cases like March 31st to Feb (doesn't have 31st)
    try:
        previous_end = now - relativedelta(months=1)
    except ValueError:
        # E.g., if today is Mar 31, 1 month ago is Feb 28/29.
        # relativedelta(months=1) usually handles this, but just in case.
        previous_end = (current_start - relativedelta(days=1)).replace(hour=23, minute=59, second=59)

    await process_comparison(
        message, 
        current_start, current_end, 
        previous_start, previous_end,
        i18n.get_text('label_this_month', user_id), 
        i18n.get_text('label_last_month', user_id),
        user_id,
        notion_writer
    )


@router.message(F.text.in_(i18n.get_all_translations('menu_cancel')), AnalyticsState.waiting_for_comparison_period_selection)
async def cancel_comparison(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Return to the analytics menu."""
    user_id = message.from_user.id
    await message.answer(
        i18n.get_text('msg_analytics_menu', user_id),
        reply_markup=await get_analytics_menu(user_id)
    )
    await state.set_state(AnalyticsState.waiting_for_menu_selection)


async def process_comparison(message: Message, current_start: datetime, current_end: datetime, previous_start: datetime, previous_end: datetime, current_label: str, previous_label: str, user_id: int, notion_writer: NotionWriter):
    """Helper function to fetch data and generate comparison chart."""
    processing_msg = await message.answer(i18n.get_text('msg_generating_report', user_id))
    
    try:
        # Fetch data for current period
        current_expenses = await notion_writer.get_expenses_by_date_range(current_start, current_end)
        
        # Fetch data for previous period up to the same point in time
        previous_expenses = await notion_writer.get_expenses_by_date_range(previous_start, previous_end)
        
        if not current_expenses and not previous_expenses:
             await processing_msg.edit_text(i18n.get_text('msg_no_data_for_comparison', user_id))
             return
             
        # Calculate totals
        current_total = sum(exp.amount for exp in current_expenses if exp.amount)
        previous_total = sum(exp.amount for exp in previous_expenses if exp.amount)
        
        # Generate chart
        chart_path = os.path.join(REPORTS_DIR, f"comp_{user_id}_{int(datetime.now().timestamp())}.png")
        generate_comparison_bar_chart(
            current_total, 
            previous_total, 
            current_label, 
            previous_label, 
            i18n.get_text('graph_spending_comparison', user_id), 
            chart_path
        )
        
        # Prepare caption indicating the time difference
        diff = current_total - previous_total
        diff_str = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
        percentage = (diff / previous_total * 100) if previous_total > 0 else (100 if current_total > 0 else 0)
        percentage_str = f"+{percentage:.1f}%" if percentage > 0 else f"{percentage:.1f}%"
        
        caption = i18n.get_text('msg_comparison_caption', user_id, 
                                current_label=current_label, current_total=f"{current_total:.2f}",
                                previous_label=previous_label, previous_total=f"{previous_total:.2f}",
                                diff=diff_str, percentage=percentage_str)
                                
        await message.answer_photo(photo=FSInputFile(chart_path), caption=caption)
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error generating comparison stats: {e}")
        await processing_msg.edit_text(i18n.get_text('msg_report_error', user_id))
