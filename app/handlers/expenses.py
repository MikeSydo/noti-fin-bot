import logging 

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime

from models.account import Account
from models.expense import Expense
from app.keyboards.reply import get_main_menu
from services.notion_writer import notion_writer
from app.keyboards.inline import get_accounts_keyboard, get_today_date_keyboard

router = Router()

logger = logging.getLogger(__name__)

class AddExpenseState(StatesGroup):
    """FSM state for expense."""
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_date = State()
    waiting_for_account = State()
    waiting_for_category = State()

@router.message(F.text == 'Додати витрату')
async def start_add_account(message: Message, state: FSMContext):
    """Start logic to add expense in notion db."""
    await state.clear()
    await message.answer(
        'Введіть назву витрати.',
        parse_mode="Markdown",
    )
    await state.set_state(AddExpenseState.waiting_for_name)

@router.message(AddExpenseState.waiting_for_name)
async def handle_expense_name_input(message: Message, state: FSMContext):
    """Handle expense name input."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    await state.update_data(name=name)
    await message.answer(
        f'Назва: {name}\nВведіть суму.',
        parse_mode="Markdown",
    )
    await state.set_state(AddExpenseState.waiting_for_amount)

@router.message(AddExpenseState.waiting_for_amount)
async def handle_amount_input(message: Message, state: FSMContext):
    """Handle amount input."""
    try:
        amount_str = message.text.strip().replace(",", ".")
        amount = Decimal(amount_str)
        if amount < 0:
            raise InvalidOperation("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer('Некоректна сума. Введіть число, наприклад: 159.90')
        return

    await state.update_data(amount=str(amount))
    await message.answer(
        f'Сума: {amount:.2f}',
        parse_mode="Markdown",
    )

    await message.answer('Введіть дату витрати у форматі ДД.ММ.РРРР (наприклад: 23.03.2026) або виберіть сьогоднішню.', 
        reply_markup=await get_today_date_keyboard())
    await state.set_state(AddExpenseState.waiting_for_date)

@router.callback_query(F.data == 'today_date', AddExpenseState.waiting_for_date)
async def hande_today_date(callback: CallbackQuery, state: FSMContext):
    """Використання поточної дати та часу."""
    await callback.answer()
    
    now = datetime.now()
    await state.update_data(date=now.isoformat())
    
    await callback.message.answer(f'Дата: {now.strftime("%d.%m.%Y %H:%M")}')
    
    await _ask_for_account(callback.message, state)

@router.message(AddExpenseState.waiting_for_date)
async def handle_date_input(message: Message, state: FSMContext):
    """Handle custom date input."""
    date_str = message.text.strip()
    
    try:
        # Parse date in format DD.MM.YYYY
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        await message.answer('Неправильний формат дати. Будь ласка, введіть у форматі ДД.ММ.РРРР (наприклад: 23.03.2026).')
        return

    await state.update_data(date=parsed_date.isoformat())
    await message.answer(f'Дата: {parsed_date.strftime("%d.%m.%Y")}')
    
    await ask_for_account(message, state)


async def ask_for_account(message: Message, state: FSMContext):
    """Ask for account."""
    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer('У вас ще немає акаунтів. Спочатку додайте акаунт у Notion.')
        await state.clear()
        return
        
    await message.answer(
        'Виберіть акаунт, з якого була витрата:',
        reply_markup=await get_accounts_keyboard(accounts)
    )
    await state.set_state(AddExpenseState.waiting_for_account)

@router.callback_query(F.data.startswith('select_account_'), AddExpenseState.waiting_for_account)
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection."""
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    await state.update_data(account_id=account_id)
    
    await ask_for_category(callback.message, state)

async def ask_for_category(message: Message, state: FSMContext):
    """Ask for category."""
    #to complete this func, need to add categories
    pass