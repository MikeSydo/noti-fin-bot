import logging 

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime

from models.expense import Expense
from app.keyboards.reply import get_main_menu
from services.notion_writer import notion_writer
from app.keyboards.inline import get_accounts_keyboard, get_today_date_keyboard, get_categories_keyboard, \
    get_expenses_keyboard

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
    
    await ask_for_account(callback.message, state)

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
        await message.answer('У вас ще немає акаунтів. Акаунт буде пропущено.')
        await state.update_data(account=None)
        await ask_for_category(message, state)
        return
        
    await message.answer(
        'Виберіть акаунт, з якого була витрата:',
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True)
    )
    await state.set_state(AddExpenseState.waiting_for_account)

@router.callback_query(F.data.startswith('select_account_'), AddExpenseState.waiting_for_account)
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection."""
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    account = await notion_writer.get_account(account_id)
    await state.update_data(account=account)
    
    await ask_for_category(callback.message, state)

@router.callback_query(F.data == 'skip_account', AddExpenseState.waiting_for_account)
async def process_skip_account(callback: CallbackQuery, state: FSMContext):
    """Handle skipping account selection."""
    await callback.answer()
    await state.update_data(account=None)
    await ask_for_category(callback.message, state)

async def ask_for_category(message: Message, state: FSMContext):
    """Ask for category."""
    categories = await notion_writer.get_categories()
    if not categories:
        await message.answer('У вас ще немає категорій. Категорію буде пропущено.')
        await state.update_data(category=None)
        await save_expense(message, state)
        return

    await message.answer(
        'Виберіть категорію витрати:',
        reply_markup=await get_categories_keyboard(categories, include_skip=True)
    )

    await state.set_state(AddExpenseState.waiting_for_category)


@router.callback_query(F.data.startswith('select_category_'), AddExpenseState.waiting_for_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Handle category selection."""
    await callback.answer()
    category_id = callback.data.replace('select_category_', '')
    category = await notion_writer.get_category(category_id)
    await state.update_data(category=category)

    await save_expense(callback.message, state)

@router.callback_query(F.data == 'skip_category', AddExpenseState.waiting_for_category)
async def process_skip_category(callback: CallbackQuery, state: FSMContext):
    """Handle skipping category selection."""
    await callback.answer()
    await state.update_data(category=None)
    await save_expense(callback.message, state)

async def save_expense(message: Message, state: FSMContext):
    """Save expense to Notion."""
    data = await state.get_data()
    await state.clear()

    try:
        amount = data.get("amount")
        account = data.get("account")
        category = data.get("category")
        expense = Expense(
            name=data["name"],
            amount=Decimal(amount) if amount is not None else None,
            date=data["date"],
            account=account if account is not None else None,
            category=category if category is not None else None
        )

        success = await notion_writer.add_expense(expense)

        if success:
            display_amount = f"{expense.amount:.2f}" if expense.amount is not None else "Пропущено"
            account_name = expense.account.name if expense.account is not None else "Пропущено"
            category_name = expense.category.name if expense.category is not None else "Пропущено"
            await message.answer(
                f"Витрату збережено!\n\n**{expense.name}**\nСума: {display_amount}\nДата: {expense.date}\n"
                f"Акаунт: {account_name}\nКатегорія: {category_name}",
                parse_mode="Markdown",
                reply_markup=await get_main_menu(),
            )
        else:
            await message.answer(
                'Не вдалось зберегти. Перевірте Notion налаштування.',
                reply_markup=await get_main_menu()
            )

    except Exception as e:
        logger.error(f"Failed to save account: {e}")
        await message.answer(
            'Виникла помилка при збереженні.',
            reply_markup=await get_main_menu(),
        )

class DeleteExpenseState(StatesGroup):
    """FSM state for expense."""
    waiting_for_name = State()
    waiting_for_selection = State()

@router.message(F.text == 'Видалити витрату')
async def start_delete_expense(message: Message, state: FSMContext):
    """Start logic to remove expense from notion db."""
    await state.clear()
    await message.answer(
        'Введіть назву витрати.',
        parse_mode="Markdown",
    )
    await state.set_state(DeleteExpenseState.waiting_for_name)

@router.message(DeleteExpenseState.waiting_for_name)
async def handle_expense_name_input(message: Message, state: FSMContext):
    """Handle expense name find."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    searching_msg = await message.answer("Триває пошук...")

    id_list = await notion_writer.find_expenses(name)
    
    await searching_msg.delete()

    if not id_list:
        await message.answer('Витрату з такою назвою не знайдено.')
        return
        
    if len(id_list) == 1:
        await state.update_data(id=id_list[0], name=name)
        await process_delete_expense(message, state)
    else:
        await state.update_data(name=name, id_list=id_list)
        await show_expenses(message, state)

async def show_expenses(message: Message, state: FSMContext, page: int = 0, edit_message: bool = False):
    data = await state.get_data()
    id_list = data.get("id_list", [])
    expenses = await notion_writer.get_expenses(id_list)
    if not expenses:
        if edit_message:
            await message.edit_text('У вас ще немає витрат.')
        else:
            await message.answer('У вас ще немає витрат.')
        await state.clear()
        return

    text = 'Знайдено більше однієї витрати за цим ім\'ям виберіть за датою:'
    keyboard = await get_expenses_keyboard(expenses, page=page)
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
    await state.set_state(DeleteExpenseState.waiting_for_selection)

@router.callback_query(F.data.startswith('exp_page_'), DeleteExpenseState.waiting_for_selection)
async def process_expense_page_selection(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for expenses list."""
    await callback.answer()
    page = int(callback.data.replace('exp_page_', ''))
    await show_expenses(callback.message, state, page=page, edit_message=True)

@router.callback_query(F.data.startswith('select_expense_'), DeleteExpenseState.waiting_for_selection)
async def process_expense_selection(callback: CallbackQuery, state: FSMContext):
    """Handle expense selection."""
    await callback.answer()
    expense_id = callback.data.replace('select_expense_', '')
    data = await state.get_data()
    await state.update_data(id=expense_id, name=data.get('name', 'Витрата'))

    await process_delete_expense(callback.message, state)


async def process_delete_expense(message: Message, state: FSMContext):
    """Handle expense deletion."""
    data = await state.get_data()
    await state.clear()

    deleting_msg = await message.answer("Видалення...", reply_markup=None)

    try:
        success = await notion_writer.delete_page(data['id'])

        await deleting_msg.delete()

        if success:
            await message.answer(
                f"Витрату {data.get('name', '')} видалено!",
                parse_mode="Markdown",
                reply_markup=await get_main_menu(),
            )
        else:
            await message.answer(
                'Не вдалось видалити. Перевірте Notion налаштування.',
                reply_markup=await get_main_menu()
            )
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        await message.answer(
            'Виникла помилка при видаленні.',
            reply_markup=await get_main_menu(),
        )