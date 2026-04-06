import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from datetime import datetime
from bot import bot
from models.group_expense import GroupExpense
from services.s3_service import upload_receipt_to_s3
from app.keyboards.reply import get_main_menu
from app.keyboards.inline import get_today_date_keyboard, get_categories_keyboard, get_group_expenses_keyboard, \
    get_skip_receipt_keyboard, get_accounts_keyboard, get_multi_select_expenses_keyboard
from services.i18n import i18n
from services.notion_writer import NotionWriter

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
    waiting_for_expenses_selection = State()


@router.message(F.text.in_(i18n.get_all_translations('btn_add_group_expense')))
async def start_add_group_expense(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Start logic to add group expense in notion db."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('grexp_enter_name', user_id),
        parse_mode="Markdown",
    )
    await state.set_state(AddGroupExpenseState.waiting_for_name)


@router.message(AddGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Handle group expense name input."""
    name = message.text.strip()
    user_id = message.from_user.id
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
async def handle_amount_input(message: Message, state: FSMContext, notion_writer: NotionWriter):
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
async def handle_today_date(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Use current date and time."""
    user_id = callback.from_user.id
    await callback.answer()

    now = datetime.now()
    await state.update_data(date=now.isoformat())

    await callback.message.answer(i18n.get_text('grexp_date', user_id, date=now.strftime("%d.%m.%Y %H:%M")))

    await ask_for_account(callback.message, state, notion_writer, user_id)


@router.message(AddGroupExpenseState.waiting_for_date)
async def handle_date_input(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Handle custom date input."""
    date_str = message.text.strip()
    user_id = message.from_user.id

    try:
        parsed_date = datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        await message.answer(i18n.get_text('grexp_invalid_date', user_id))
        return

    await state.update_data(date=parsed_date.isoformat())
    await message.answer(i18n.get_text('grexp_date', user_id, date=parsed_date.strftime("%d.%m.%Y")))

    await ask_for_account(message, state, notion_writer, user_id)


async def ask_for_account(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int = None):
    """Ask for account."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer(i18n.get_text('grexp_no_accounts', user_id))
        await state.update_data(account=None)
        await ask_for_category(message, state, notion_writer, user_id)
        return

    await message.answer(
        i18n.get_text('grexp_choose_account', user_id),
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True, user_id=user_id)
    )
    await state.set_state(AddGroupExpenseState.waiting_for_account)


@router.callback_query(F.data.startswith('select_account_'), AddGroupExpenseState.waiting_for_account)
async def process_account_selection(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle account selection."""
    user_id = callback.from_user.id
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    account = await notion_writer.get_account(account_id)
    await state.update_data(account=account)

    await ask_for_category(callback.message, state, notion_writer, user_id)


@router.callback_query(F.data == 'skip_account', AddGroupExpenseState.waiting_for_account)
async def process_skip_account(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle skipping account selection."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(account=None)
    await ask_for_category(callback.message, state, notion_writer, user_id)


async def ask_for_category(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int = None):
    """Ask for category."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    categories = await notion_writer.get_categories()
    if not categories:
        await message.answer(i18n.get_text('grexp_no_categories', user_id))
        await state.update_data(category=None)
        await ask_for_receipt(message, state, notion_writer, user_id)
        return

    await message.answer(
        i18n.get_text('grexp_choose_category', user_id),
        reply_markup=await get_categories_keyboard(categories, include_skip=True, user_id=user_id)
    )

    await state.set_state(AddGroupExpenseState.waiting_for_category)


@router.callback_query(F.data.startswith('select_category_'), AddGroupExpenseState.waiting_for_category)
async def process_category_selection(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle category selection."""
    user_id = callback.from_user.id
    await callback.answer()
    category_id = callback.data.replace('select_category_', '')
    category = await notion_writer.get_category(category_id)
    await state.update_data(category=category)

    await ask_for_receipt(callback.message, state, notion_writer, user_id)


@router.callback_query(F.data == 'skip_category', AddGroupExpenseState.waiting_for_category)
async def process_skip_category(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle skipping category selection."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(category=None)
    await ask_for_receipt(callback.message, state, notion_writer, user_id)


async def ask_for_receipt(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int = None):
    """Ask for receipt document/photo."""
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    await message.answer(
        i18n.get_text('grexp_send_receipt', user_id),
        reply_markup=await get_skip_receipt_keyboard(user_id)
    )
    await state.set_state(AddGroupExpenseState.waiting_for_receipt)


@router.callback_query(F.data == 'skip_receipt', AddGroupExpenseState.waiting_for_receipt)
async def process_skip_receipt(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle skipping receipt upload."""
    user_id = callback.from_user.id
    await callback.answer()
    await state.update_data(receipt_url=None)

    await ask_for_expenses_selection(callback.message, state, notion_writer, user_id)


@router.message(AddGroupExpenseState.waiting_for_receipt, F.photo | F.document)
async def process_receipt_document(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Handle receipt as document/photo and upload."""
    user_id = message.from_user.id
    await message.answer(i18n.get_text('grexp_uploading_receipt', user_id))

    try:
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id

        file_url = None
        if file_id:
            file = await bot.get_file(file_id)
            file_bytes_io = await bot.download_file(file.file_path)
            file_bytes = file_bytes_io.read()
            file_url = await upload_receipt_to_s3(file_bytes, file_extension="jpg")
        
        await state.update_data(receipt_url=file_url)

        await message.answer(i18n.get_text('grexp_receipt_saved', user_id))
        await ask_for_expenses_selection(message, state, notion_writer, user_id)

    except Exception as e:
        logger.error(f"Failed to process and upload receipt: {e}")
        await message.answer(i18n.get_text('grexp_load_failed', user_id))


async def ask_for_expenses_selection(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int):
    """Ask for choosing relations from db expenses."""
    expenses = await notion_writer.get_expenses_list()
    if not expenses:
        await message.answer(i18n.get_text('grexp_no_expenses_available', user_id))
        await save_group_expense(message, state, notion_writer, user_id)
        return

    await state.update_data(selected_expenses_ids=[])
    await state.set_state(AddGroupExpenseState.waiting_for_expenses_selection)
    await show_expenses_selection(message, state, notion_writer, user_id)


async def show_expenses_selection(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int, page: int = 0, edit_message: bool = False):
    """Show the multiselect interface for expenses with checkmarks."""
    # We fetch a list of recent expenses to select from
    expenses = await notion_writer.get_expenses_list()
    data = await state.get_data()
    selected_ids = set(data.get("selected_expenses_ids", []))

    text = i18n.get_text('grexp_choose_expenses', user_id)
    keyboard = await get_multi_select_expenses_keyboard(expenses, selected_ids, page, user_id)

    if edit_message:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith('toggle_grexpense_rel_'), AddGroupExpenseState.waiting_for_expenses_selection)
async def process_expense_toggle(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Toggle the selection of an expense."""
    user_id = callback.from_user.id
    expense_id = callback.data.replace('toggle_grexpense_rel_', '')
    data = await state.get_data()
    selected_ids = set(data.get("selected_expenses_ids", []))

    if expense_id in selected_ids:
        selected_ids.remove(expense_id)
    else:
        selected_ids.add(expense_id)

    await state.update_data(selected_expenses_ids=list(selected_ids))
    
    # Needs to figure out current page from the keyboard, unfortunately aiogram 3 
    # doesn't make it easy to pass page via callback data if we just do toggle. 
    # We just keep page 0 or re-parse. We fix to page 0 for simplicity.
    await show_expenses_selection(callback.message, state, notion_writer, user_id, page=0, edit_message=True)
    await callback.answer()


@router.callback_query(F.data.startswith('multiexp_page_'), AddGroupExpenseState.waiting_for_expenses_selection)
async def process_expenses_selection_page(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle pagination for expenses multi-select list."""
    user_id = callback.from_user.id
    page = int(callback.data.replace('multiexp_page_', ''))
    await show_expenses_selection(callback.message, state, notion_writer, user_id, page=page, edit_message=True)
    await callback.answer()


@router.callback_query(F.data == 'finish_expenses_selection', AddGroupExpenseState.waiting_for_expenses_selection)
async def process_finish_expenses_selection(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Finish the expenses multi-select and save."""
    user_id = callback.from_user.id
    await callback.answer()

    await callback.message.delete()
    await save_group_expense(callback.message, state, notion_writer, user_id)


async def save_group_expense(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int):
    """Final save of the group expense."""
    data = await state.get_data()
    await state.clear()

    try:
        amount = data.get("amount")
        account = data.get("account")
        category = data.get("category")
        selected_expenses_ids = data.get("selected_expenses_ids", [])
        
        expense = GroupExpense(
            name=data["name"],
            amount=Decimal(amount) if amount is not None else None,
            date=data["date"],
            account=account if account is not None else None,
            category=category if category is not None else None,
            receipt_url=data.get("receipt_url"),
            expenses_relations=selected_expenses_ids
        )

        success = await notion_writer.add_group_expense(expense)

        if success:
            skipped_text = i18n.get_text('txt_skipped', user_id)
            display_amount = f"{expense.amount:.2f}" if expense.amount is not None else skipped_text
            account_name = expense.account.name if expense.account is not None else skipped_text
            category_name = expense.category.name if expense.category is not None else skipped_text
            await message.answer(
                i18n.get_text('grexp_saved', user_id, name=expense.name, amount=display_amount, date=expense.date,
                              account=account_name, category=category_name),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id),
            )
        else:
            await message.answer(
                i18n.get_text('grexp_save_failed', user_id),
                reply_markup=await get_main_menu(user_id)
            )
    except Exception as e:
        logger.error(f"Failed to save group expense: {e}")
        await message.answer(
            i18n.get_text('grexp_save_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )


class DeleteGroupExpenseState(StatesGroup):
    """FSM state for deleting group expense."""
    waiting_for_name = State()
    waiting_for_selection = State()


@router.message(F.text.in_(i18n.get_all_translations('btn_del_group_expense')))
async def start_delete_group_expense(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Start logic to remove group expense from notion db."""
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        i18n.get_text('grexp_enter_name', user_id),
        parse_mode="Markdown",
    )
    await state.set_state(DeleteGroupExpenseState.waiting_for_name)


@router.message(DeleteGroupExpenseState.waiting_for_name)
async def handle_group_expense_name_input_for_delete(message: Message, state: FSMContext, notion_writer: NotionWriter):
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
        await process_delete_group_expense(message, state, notion_writer, user_id)
    else:
        await state.update_data(name=name, id_list=id_list)
        await show_group_expenses(message, state, notion_writer, user_id=user_id)


async def show_group_expenses(message: Message, state: FSMContext, notion_writer: NotionWriter, page: int = 0, edit_message: bool = False, user_id: int = None):
    data = await state.get_data()
    if user_id is None:
        user_id = message.from_user.id if message.from_user else state.key.user_id

    id_list = data.get("id_list", [])
    expenses = await notion_writer.get_group_expenses_by_ids(id_list)
    if not expenses:
        if edit_message:
            await message.edit_text(i18n.get_text('grexp_no_expenses', user_id))
        else:
            await message.answer(i18n.get_text('grexp_no_expenses', user_id))
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
async def process_group_expense_page_selection(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle pagination for group expenses list."""
    user_id = callback.from_user.id
    await callback.answer()
    page = int(callback.data.replace('grexp_page_', ''))
    await show_group_expenses(callback.message, state, notion_writer, page=page, edit_message=True, user_id=user_id)


@router.callback_query(F.data.startswith('select_grexpense_'), DeleteGroupExpenseState.waiting_for_selection)
async def process_group_expense_selection(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    """Handle group expense selection."""
    user_id = callback.from_user.id
    await callback.answer()
    expense_id = callback.data.replace('select_grexpense_', '')
    data = await state.get_data()
    await state.update_data(id=expense_id, name=data.get('name', ''))

    await process_delete_group_expense(callback.message, state, notion_writer, user_id)


async def process_delete_group_expense(message: Message, state: FSMContext, notion_writer: NotionWriter, user_id: int = None):
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
        logger.error(f"Failed to delete group expense: {e}")
        await message.answer(
            i18n.get_text('grexp_delete_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )
