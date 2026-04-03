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
from services.i18n import i18n

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

@router.message(F.text.in_(i18n.get_all_translations('btn_add_group_expense')))
async def start_add_group_expense(message: Message, state: FSMContext):
    """Start logic to add group expense in notion db."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('grexp_enter_name', user_id),
        parse_mode="Markdown",
    )
    await state.set_state(AddGroupExpenseState.waiting_for_name)

@router.message(AddGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input(message: Message, state: FSMContext):
    """Handle group expense name input."""
    user_id = message.from_user.id
    name = message.text.strip()
    if not name:
        await message.answer(i18n.get_text('grexp_name_empty', user_id))
        return

    await state.update_data(name=name)
    await message.answer(
        i18n.get_text('grexp_name_entered', user_id, name=name),
        parse_mode="Markdown",
    )
    await state.set_state(AddGroupExpenseState.waiting_for_amount)

@router.message(AddGroupExpenseState.waiting_for_amount)
async def handle_amount_input(message: Message, state: FSMContext):
    """Handle amount input."""
    user_id = message.from_user.id
    try:
        amount_str = message.text.strip().replace(",", ".")
        amount = Decimal(amount_str)
        if amount < 0:
            raise InvalidOperation("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer(i18n.get_text('grexp_invalid_amount', user_id))
        return

    await state.update_data(amount=str(amount))
    await message.answer(
        i18n.get_text('grexp_amount_saved', user_id, amount=f'{amount:.2f}'),
        parse_mode="Markdown",
    )

    await message.answer(i18n.get_text('grexp_enter_date', user_id),
        reply_markup=await get_today_date_keyboard(user_id))
    await state.set_state(AddGroupExpenseState.waiting_for_date)

@router.callback_query(F.data == 'today_date', AddGroupExpenseState.waiting_for_date)
async def handle_today_date(callback: CallbackQuery, state: FSMContext):
    """Використання поточної дати та часу."""
    user_id = callback.from_user.id
    await callback.answer()

    now = datetime.now()
    await state.update_data(date=now.isoformat())

    await callback.message.answer(i18n.get_text('grexp_date', user_id, date=now.strftime("%d.%m.%Y %H:%M")))

    await ask_for_account(callback.message, state, user_id)

@router.message(AddGroupExpenseState.waiting_for_date)
async def handle_date_input(message: Message, state: FSMContext):
    """Handle custom date input."""
    user_id = message.from_user.id
    date_str = message.text.strip()

    try:
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        await message.answer(i18n.get_text('grexp_invalid_date', user_id))
        return

    await state.update_data(date=parsed_date.isoformat())
    await message.answer(i18n.get_text('grexp_date', user_id, date=parsed_date.strftime("%d.%m.%Y")))

    await ask_for_account(message, state, user_id)


async def ask_for_account(message: Message, state: FSMContext, user_id: int = None):
    """Ask for account."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer(i18n.get_text('grexp_no_accounts', user_id))
        await state.update_data(account=None)
        await ask_for_category(message, state, user_id)
        return

    await message.answer(
        i18n.get_text('grexp_choose_account', user_id),
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True, user_id=user_id)
    )
    await state.set_state(AddGroupExpenseState.waiting_for_account)

@router.callback_query(F.data.startswith('select_account_'), AddGroupExpenseState.waiting_for_account)
async def process_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection."""
    user_id = callback.from_user.id
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    account = await notion_writer.get_account(account_id)
    await state.update_data(account=account)

    await ask_for_category(callback.message, state, user_id)

@router.callback_query(F.data == 'skip_account', AddGroupExpenseState.waiting_for_account)
async def process_skip_account(callback: CallbackQuery, state: FSMContext):
    """Handle skipping account selection."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(account=None)
    await ask_for_category(callback.message, state, user_id)

async def ask_for_category(message: Message, state: FSMContext, user_id: int = None):
    """Ask for category."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    categories = await notion_writer.get_categories()
    if not categories:
        await message.answer(i18n.get_text('grexp_no_categories', user_id))
        await state.update_data(category=None)
        await ask_for_receipt(message, state, user_id)
        return

    await message.answer(
        i18n.get_text('grexp_choose_category', user_id),
        reply_markup=await get_categories_keyboard(categories, include_skip=True, user_id=user_id)
    )

    await state.set_state(AddGroupExpenseState.waiting_for_category)

@router.callback_query(F.data.startswith('select_category_'), AddGroupExpenseState.waiting_for_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Handle category selection."""
    user_id = callback.from_user.id
    await callback.answer()
    category_id = callback.data.replace('select_category_', '')
    category = await notion_writer.get_category(category_id)
    await state.update_data(category=category)

    await ask_for_receipt(callback.message, state, user_id)

@router.callback_query(F.data == 'skip_category', AddGroupExpenseState.waiting_for_category)
async def process_skip_category(callback: CallbackQuery, state: FSMContext):
    """Handle skipping category selection."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(category=None)
    await ask_for_receipt(callback.message, state, user_id)

async def ask_for_receipt(message: Message, state: FSMContext, user_id: int = None):
    """Ask for receipt file."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    await message.answer(
        i18n.get_text('grexp_send_receipt', user_id),
        reply_markup=await get_skip_receipt_keyboard(user_id)
    )
    await state.set_state(AddGroupExpenseState.waiting_for_receipt)

@router.message(AddGroupExpenseState.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext):
    """Handle uploaded receipt."""
    user_id = message.from_user.id
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        file = await message.bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        await state.update_data(receipt_url=file_url)
        await ask_for_related_expenses(message, state, user_id)
    except Exception as e:
        logger.error(f"Failed to process photo receipt: {e}")
        await message.answer(i18n.get_text('grexp_receipt_not_photo', user_id))

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
    user_id = message.from_user.id
    await message.answer(i18n.get_text('grexp_receipt_not_photo', user_id))

@router.message(AddGroupExpenseState.waiting_for_receipt)
async def process_receipt_catch_all(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer(i18n.get_text('grexp_receipt_not_photo', user_id))

@router.callback_query(F.data == 'skip_receipt', AddGroupExpenseState.waiting_for_receipt)
async def process_skip_receipt(callback: CallbackQuery, state: FSMContext):
    """Handle skipping receipt selection."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(receipt_url=None)
    await ask_for_related_expenses(callback.message, state, user_id)

async def ask_for_related_expenses(message: Message, state: FSMContext, page: int = 0, edit_message: bool = False, user_id: int = None):
    """Ask for related personal expenses using multi-select."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    expenses = await notion_writer.get_expenses_list()
    if not expenses:
        msg_text = i18n.get_text('grexp_no_expenses_to_relate', user_id)
        if edit_message:
            await message.edit_text(msg_text)
        else:
            await message.answer(msg_text)
        await save_group_expense(message, state, user_id)
        return

    data = await state.get_data()
    selected_ids = data.get("selected_expenses", set())

    text = i18n.get_text('grexp_select_related', user_id)
    keyboard = await get_multi_select_expenses_keyboard(expenses, selected_ids, page=page, user_id=user_id)

    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

    await state.set_state(AddGroupExpenseState.waiting_for_related_expenses)

@router.callback_query(F.data.startswith('multiexp_page_'), AddGroupExpenseState.waiting_for_related_expenses)
async def process_multi_expense_page(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for multi-select expenses list."""
    user_id = callback.from_user.id
    await callback.answer()
    page = int(callback.data.replace('multiexp_page_', ''))
    # Save the current page into state so toggles can stay on it
    await state.update_data(multiexp_page=page)
    await ask_for_related_expenses(callback.message, state, page=page, edit_message=True, user_id=user_id)

@router.callback_query(F.data.startswith('toggle_grexpense_rel_'), AddGroupExpenseState.waiting_for_related_expenses)
async def process_toggle_related_expense(callback: CallbackQuery, state: FSMContext):
    """Handle toggling a related personal expense."""
    user_id = callback.from_user.id
    expense_id = callback.data.replace('toggle_grexpense_rel_', '')
    data = await state.get_data()
    selected_ids = data.get("selected_expenses", set())

    if expense_id in selected_ids:
        selected_ids.remove(expense_id)
    else:
        selected_ids.add(expense_id)

    await state.update_data(selected_expenses=selected_ids)

    # find current page from state
    current_page = data.get("multiexp_page", 0)

    expenses = await notion_writer.get_expenses_list()
    keyboard = await get_multi_select_expenses_keyboard(expenses, selected_ids, page=current_page, user_id=user_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'finish_expenses_selection', AddGroupExpenseState.waiting_for_related_expenses)
async def process_finish_related_expenses(callback: CallbackQuery, state: FSMContext):
    """Finish related expenses selection and save."""
    user_id = callback.from_user.id
    await callback.answer()
    await save_group_expense(callback.message, state, user_id)

async def save_group_expense(message: Message, state: FSMContext, user_id: int = None):
    """Save group expense to Notion."""
    data = await state.get_data()
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    await state.clear()

    try:
        amount = data.get("amount")
        account = data.get("account")
        expense = GroupExpense(
            name=data["name"],
            amount=Decimal(amount) if amount is not None else None,
            date=data["date"],
            account=account if account is not None else None,
            receipt_url=data.get("receipt_url"),
            expenses_relations=list(data.get("selected_expenses", set()))
        )

        success = await notion_writer.add_group_expense(expense)

        if success:
            display_amount = f"{expense.amount:.2f}" if expense.amount is not None else "0.00"
            await message.answer(
                i18n.get_text('grexp_saved', user_id, name=expense.name),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id),
            )
        else:
            await message.answer(
                i18n.get_text('grexp_save_failed', user_id),
                reply_markup=await get_main_menu(user_id)
            )

    except Exception as e:
        logger.error(f"Failed to save account: {e}")
        await message.answer(
            i18n.get_text('grexp_save_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )

class DeleteGroupExpenseState(StatesGroup):
    """FSM state for group expense deletion."""
    waiting_for_name = State()
    waiting_for_selection = State()

@router.message(F.text.in_(i18n.get_all_translations('btn_del_group_expense')))
async def start_delete_group_expense(message: Message, state: FSMContext):
    """Start logic to remove group expense from notion db."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('grexp_enter_delete_name', user_id),
        parse_mode="Markdown",
    )
    await state.set_state(DeleteGroupExpenseState.waiting_for_name)

@router.message(DeleteGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input_del(message: Message, state: FSMContext):
    """Handle group expense name find."""
    name = message.text.strip()
    user_id = message.from_user.id
    if not name:
        await message.answer(i18n.get_text('grexp_name_empty', user_id))
        return

    searching_msg = await message.answer(i18n.get_text('grexp_searching', user_id))

    id_list = await notion_writer.find_group_expenses(name)

    await searching_msg.delete()

    if not id_list:
        await message.answer(i18n.get_text('grexp_not_found', user_id))
        return

    if len(id_list) == 1:
        await state.update_data(id=id_list[0], name=name)
        await process_delete_group_expense(message, state, user_id)
    else:
        await state.update_data(name=name, id_list=id_list)
        await show_group_expenses(message, state, user_id)

async def show_group_expenses(message: Message, state: FSMContext, user_id: int, page: int = 0, edit_message: bool = False):
    data = await state.get_data()
    id_list = data.get("id_list", [])
    expenses = await notion_writer.get_group_expenses_by_ids(id_list)
    if not expenses:
        if edit_message:
            await message.edit_text(i18n.get_text('grexp_not_found', user_id))
        else:
            await message.answer(i18n.get_text('grexp_not_found', user_id))
        await state.clear()
        return

    text = i18n.get_text('grexp_multiple_found', user_id)
    keyboard = await get_group_expenses_keyboard(expenses, page=page, user_id=user_id)

    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
    await state.set_state(DeleteGroupExpenseState.waiting_for_selection)

@router.callback_query(F.data.startswith('grexp_page_'), DeleteGroupExpenseState.waiting_for_selection)
async def process_group_expense_page(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for group expenses list."""
    user_id = callback.from_user.id
    await callback.answer()
    page = int(callback.data.replace('grexp_page_', ''))
    await show_group_expenses(callback.message, state, user_id=user_id, page=page, edit_message=True)

@router.callback_query(F.data.startswith('select_grexpense_'), DeleteGroupExpenseState.waiting_for_selection)
async def process_group_expense_selection(callback: CallbackQuery, state: FSMContext):
    """Handle group expense selection."""
    user_id = callback.from_user.id
    await callback.answer()
    expense_id = callback.data.replace('select_grexpense_', '')
    data = await state.get_data()
    await state.update_data(id=expense_id, name=data.get('name', 'Витрата'))

    await process_delete_group_expense(callback.message, state, user_id)

async def process_delete_group_expense(message: Message, state: FSMContext, user_id: int = None):
    """Handle group expense deletion."""
    data = await state.get_data()
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    await state.clear()

    deleting_msg = await message.answer(i18n.get_text('grexp_deleting', user_id), reply_markup=None)

    try:
        success = await notion_writer.delete_page(data['id'])

        await deleting_msg.delete()

        if success:
            await message.answer(
                i18n.get_text('grexp_deleted', user_id, name=data.get('name', '')),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id),
            )
        else:
            await message.answer(
                i18n.get_text('grexp_delete_failed', user_id),
                reply_markup=await get_main_menu(user_id)
            )
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        await message.answer(
            i18n.get_text('grexp_delete_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )
