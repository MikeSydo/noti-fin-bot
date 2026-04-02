import logging
import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime

from models.group_expense import GroupExpense
from app.keyboards.reply import get_main_menu
from services.notion_writer import notion_writer
from app.keyboards.inline import get_accounts_keyboard, get_today_date_keyboard, get_categories_keyboard, \
    get_group_expenses_keyboard, get_skip_receipt_keyboard, get_multi_select_expenses_keyboard

router = Router()

logger = logging.getLogger(__name__)

class AddGroupExpenseState(StatesGroup):
    """FSM state for group expense."""
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_date = State()
    waiting_for_account = State()
    waiting_for_category = State()
    waiting_for_receipt = State()
    waiting_for_related_expenses = State()

@router.message(F.text == 'Додати групову витрату')
async def start_add_group_expense(message: Message, state: FSMContext):
    """Start logic to add group expense in notion db."""
    await state.clear()
    await message.answer(
        'Введіть назву групової витрати.',
        parse_mode="Markdown",
    )
    await state.set_state(AddGroupExpenseState.waiting_for_name)

@router.message(AddGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input(message: Message, state: FSMContext):
    """Handle group expense name input."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    await state.update_data(name=name)
    await message.answer(
        f'Назва: {name}\nВведіть суму.',
        parse_mode="Markdown",
    )
    await state.set_state(AddGroupExpenseState.waiting_for_amount)

@router.message(AddGroupExpenseState.waiting_for_amount)
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
    await state.set_state(AddGroupExpenseState.waiting_for_date)

@router.callback_query(F.data == 'today_date', AddGroupExpenseState.waiting_for_date)
async def handle_today_date(callback: CallbackQuery, state: FSMContext):
    """Використання поточної дати та часу."""
    await callback.answer()

    now = datetime.now()
    await state.update_data(date=now.isoformat())

    await callback.message.answer(f'Дата: {now.strftime("%d.%m.%Y %H:%M")}')

    await ask_for_account(callback.message, state)

@router.message(AddGroupExpenseState.waiting_for_date)
async def handle_date_input(message: Message, state: FSMContext):
    """Handle custom date input."""
    date_str = message.text.strip()

    try:
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
        'Виберіть акаунт, з якого буде витрата:',
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True)
    )
    await state.set_state(AddGroupExpenseState.waiting_for_account)

@router.callback_query(F.data.startswith('select_account_'), AddGroupExpenseState.waiting_for_account)
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection."""
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    account = await notion_writer.get_account(account_id)
    await state.update_data(account=account)

    await ask_for_category(callback.message, state)

@router.callback_query(F.data == 'skip_account', AddGroupExpenseState.waiting_for_account)
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
        await ask_for_receipt(message, state)
        return

    await message.answer(
        'Виберіть категорію витрати:',
        reply_markup=await get_categories_keyboard(categories, include_skip=True)
    )

    await state.set_state(AddGroupExpenseState.waiting_for_category)

@router.callback_query(F.data.startswith('select_category_'), AddGroupExpenseState.waiting_for_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Handle category selection."""
    await callback.answer()
    category_id = callback.data.replace('select_category_', '')
    category = await notion_writer.get_category(category_id)
    await state.update_data(category=category)

    await ask_for_receipt(callback.message, state)

@router.callback_query(F.data == 'skip_category', AddGroupExpenseState.waiting_for_category)
async def process_skip_category(callback: CallbackQuery, state: FSMContext):
    """Handle skipping category selection."""
    await callback.answer()
    await state.update_data(category=None)
    await ask_for_receipt(callback.message, state)

async def ask_for_receipt(message: Message, state: FSMContext):
    """Ask for receipt file."""
    await message.answer(
        'Надішліть фото або файл чеку, або пропустіть цей крок:',
        reply_markup=await get_skip_receipt_keyboard()
    )
    await state.set_state(AddGroupExpenseState.waiting_for_receipt)

@router.message(AddGroupExpenseState.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext):
    """Handle uploaded receipt."""
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        file = await message.bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        await state.update_data(receipt_url=file_url)
        await ask_for_related_expenses(message, state)
    except Exception as e:
        logger.error(f"Failed to process photo receipt: {e}")
        await message.answer("Виникла помилка при обробці фото/файлу. Спробуйте ще раз або пропустіть.")

@router.message(AddGroupExpenseState.waiting_for_receipt, F.document)
async def process_receipt_document(message: Message, state: FSMContext):
    """Handle uploaded receipt document."""
    try:
        file_id = message.document.file_id

        file = await message.bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        await state.update_data(receipt_url=file_url)
        await ask_for_related_expenses(message, state)
    except Exception as e:
        logger.error(f"Failed to process document receipt: {e}")
        await message.answer("Виникла помилка при обробці документа. Спробуйте ще раз або пропустіть.")

@router.message(AddGroupExpenseState.waiting_for_receipt, F.text)
async def process_receipt_wrong_format(message: Message, state: FSMContext):
    await message.answer("Будь ласка, надішліть фото або документ, або натисніть кнопку 'Пропустити'.")

@router.message(AddGroupExpenseState.waiting_for_receipt)
async def process_receipt_catch_all(message: Message, state: FSMContext):
    await message.answer("Будь ласка, надішліть фото або документ, або натисніть кнопку 'Пропустити'.")

@router.callback_query(F.data == 'skip_receipt', AddGroupExpenseState.waiting_for_receipt)
async def process_skip_receipt(callback: CallbackQuery, state: FSMContext):
    """Handle skipping receipt selection."""
    await callback.answer()
    await state.update_data(receipt_url=None)
    await ask_for_related_expenses(callback.message, state)

async def ask_for_related_expenses(message: Message, state: FSMContext, edit_message: bool = False):
    """Ask for related expenses."""
    await state.set_state(AddGroupExpenseState.waiting_for_related_expenses)
    
    data = await state.get_data()
    # Cache recent expenses in state to avoid re-fetching on pagination
    if 'recent_expenses' not in data:
        expenses = await notion_writer.get_recent_expenses(limit=15)
        # Store as dicts or keep in memory. We'll store dict representations
        expenses_dicts = [e.model_dump() for e in expenses]
        await state.update_data(recent_expenses=expenses_dicts, selected_expense_ids=set(), multiexp_page=0)
        data = await state.get_data()
    else:
        from models.expense import Expense
        expenses = [Expense.model_validate(e) for e in data['recent_expenses']]
        
    selected_ids = data.get('selected_expense_ids', set())
    page = data.get('multiexp_page', 0)
    
    if not expenses:
        if not edit_message:
            await message.answer('У вас немає недавніх витрат для зв\'язку. Зберігаю...', reply_markup=None)
        await save_group_expense(message, state)
        return

    text = "Виберіть звичайні витрати (за останні дні), які входять до цієї групової:"
    keyboard = await get_multi_select_expenses_keyboard(expenses, selected_ids, page)
    
    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith('toggle_grexpense_rel_'), AddGroupExpenseState.waiting_for_related_expenses)
async def process_toggle_related_expense(callback: CallbackQuery, state: FSMContext):
    expense_id = callback.data.replace('toggle_grexpense_rel_', '')
    data = await state.get_data()
    selected_ids = data.get('selected_expense_ids', set())
    
    if expense_id in selected_ids:
        selected_ids.remove(expense_id)
    else:
        selected_ids.add(expense_id)
        
    await state.update_data(selected_expense_ids=selected_ids)
    await ask_for_related_expenses(callback.message, state, edit_message=True)
    await callback.answer()


@router.callback_query(F.data.startswith('multiexp_page_'), AddGroupExpenseState.waiting_for_related_expenses)
async def process_multiexp_page_selection(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for related expenses."""
    page = int(callback.data.replace('multiexp_page_', ''))
    await state.update_data(multiexp_page=page)
    await ask_for_related_expenses(callback.message, state, edit_message=True)
    await callback.answer()


@router.callback_query(F.data == 'finish_expenses_selection', AddGroupExpenseState.waiting_for_related_expenses)
async def process_finish_related_expenses(callback: CallbackQuery, state: FSMContext):
    """Finish selection and save."""
    await callback.answer()
    await save_group_expense(callback.message, state)


async def save_group_expense(message: Message, state: FSMContext):
    """Save group expense to Notion."""
    data = await state.get_data()
    await state.clear()

    try:
        amount = data.get("amount")
        account = data.get("account")
        category = data.get("category")
        receipt_url = data.get("receipt_url")
        selected_expense_ids = list(data.get("selected_expense_ids", set()))

        expense = GroupExpense(
            name=data["name"],
            amount=Decimal(amount) if amount is not None else Decimal('0'),
            date=data["date"],
            account=account,
            category=category,
            receipt_url=receipt_url,
            expenses_relations=selected_expense_ids
        )

        success = await notion_writer.add_group_expense(expense)

        if success:
            display_amount = f"{expense.amount:.2f}"
            account_name = expense.account.name if expense.account is not None else "Пропущено"
            category_name = expense.category.name if expense.category is not None else "Пропущено"
            receipt_status = "Додано" if receipt_url else "Пропущено"
            relations_count = len(selected_expense_ids)
            await message.answer(
                f"Групову витрату збережено!\n\n**{expense.name}**\nСума: {display_amount}\nДата: {expense.date}\n"
                f"Акаунт: {account_name}\nКатегорія: {category_name}\nЧек: {receipt_status}\n"
                f"Прив'язаних витрат: {relations_count}",
                parse_mode="Markdown",
                reply_markup=await get_main_menu(),
            )
        else:
            await message.answer(
                'Не вдалось зберегти. Перевірте Notion налаштування.',
                reply_markup=await get_main_menu()
            )

    except Exception as e:
        logger.error(f"Failed to save group expense: {e}")
        await message.answer(
            'Виникла помилка при збереженні.',
            reply_markup=await get_main_menu(),
        )

class DeleteGroupExpenseState(StatesGroup):
    """FSM state for deleting group expense."""
    waiting_for_name = State()
    waiting_for_selection = State()

@router.message(F.text == 'Видалити групову витрату')
async def start_delete_group_expense(message: Message, state: FSMContext):
    """Start logic to remove group expense from notion db."""
    await state.clear()
    await message.answer(
        'Введіть назву групової витрати.',
        parse_mode="Markdown",
    )
    await state.set_state(DeleteGroupExpenseState.waiting_for_name)

@router.message(DeleteGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input(message: Message, state: FSMContext):
    """Handle group expense name find."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    searching_msg = await message.answer("Триває пошук...")

    id_list = await notion_writer.find_group_expenses(name)

    await searching_msg.delete()

    if not id_list:
        await message.answer('Групову витрату з такою назвою не знайдено.')
        return

    if len(id_list) == 1:
        await state.update_data(id=id_list[0], name=name)
        await process_delete_group_expense(message, state)
    else:
        await state.update_data(name=name, id_list=id_list)
        await show_group_expenses(message, state)

async def show_group_expenses(message: Message, state: FSMContext, page: int = 0, edit_message: bool = False):
    data = await state.get_data()
    id_list = data.get("id_list", [])
    expenses = await notion_writer.get_group_expenses(id_list)
    if not expenses:
        if edit_message:
            await message.edit_text('У вас ще немає групових витрат.')
        else:
            await message.answer('У вас ще немає групових витрат.')
        await state.clear()
        return

    text = 'Знайдено більше однієї витрати за цим ім\'ям виберіть за датою:'
    keyboard = await get_group_expenses_keyboard(expenses, page=page)

    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
    await state.set_state(DeleteGroupExpenseState.waiting_for_selection)

@router.callback_query(F.data.startswith('grexp_page_'), DeleteGroupExpenseState.waiting_for_selection)
async def process_grexpense_page_selection(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for group expenses list."""
    await callback.answer()
    page = int(callback.data.replace('grexp_page_', ''))
    await show_group_expenses(callback.message, state, page=page, edit_message=True)

@router.callback_query(F.data.startswith('select_grexpense_'), DeleteGroupExpenseState.waiting_for_selection)
async def process_grexpense_selection(callback: CallbackQuery, state: FSMContext):
    """Handle group expense selection."""
    await callback.answer()
    expense_id = callback.data.replace('select_grexpense_', '')
    data = await state.get_data()
    await state.update_data(id=expense_id, name=data.get('name', 'Витрата'))

    await process_delete_group_expense(callback.message, state)


async def process_delete_group_expense(message: Message, state: FSMContext):
    """Handle group expense deletion."""
    data = await state.get_data()
    await state.clear()

    deleting_msg = await message.answer("Видалення...", reply_markup=None)

    try:
        success = await notion_writer.delete_page(data['id'])

        await deleting_msg.delete()

        if success:
            await message.answer(
                f"Групову витрату {data.get('name', '')} видалено!",
                parse_mode="Markdown",
                reply_markup=await get_main_menu(),
            )
        else:
            await message.answer(
                'Не вдалось видалити. Перевірте Notion налаштування.',
                reply_markup=await get_main_menu()
            )
    except Exception as e:
        logger.error(f"Failed to delete group expense: {e}")
        await message.answer(
            'Виникла помилка при видаленні.',
            reply_markup=await get_main_menu(),
        )
