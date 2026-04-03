import logging 

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from models.account import Account
from app.keyboards.reply import get_main_menu
from services.notion_writer import notion_writer
from app.keyboards.inline import get_skip_attribute_keyboard
from app.keyboards.inline import get_accounts_keyboard
from services.i18n import i18n

router = Router()

logger = logging.getLogger(__name__)

class AddAccountState(StatesGroup):
    """FSM state for accounts."""
    waiting_for_name = State()
    waiting_for_initial_amount = State()

@router.message(F.text.in_(i18n.get_all_translations('btn_add_account')))
async def start_add_account(message: Message, state: FSMContext):
    """Start logic to add account in notion db."""
    await state.clear()
    await message.answer(
        i18n.get_text('acc_enter_name', message.from_user.id),
        parse_mode="Markdown",
    )
    await state.set_state(AddAccountState.waiting_for_name)

@router.message(AddAccountState.waiting_for_name)
async def handle_account_name_input(message: Message, state: FSMContext):
    """Handle account name input."""
    name = message.text.strip()
    user_id = message.from_user.id
    if not name:
        await message.answer(i18n.get_text('acc_name_empty', user_id))
        return

    await state.update_data(name=name)
    await message.answer(
        i18n.get_text('acc_name_entered', user_id, name=name),
        parse_mode="Markdown",
        reply_markup=await get_skip_attribute_keyboard(user_id),
    )
    await state.set_state(AddAccountState.waiting_for_initial_amount)

@router.callback_query(F.data == 'skip_attribute', AddAccountState.waiting_for_initial_amount)
async def handle_skip_initial_amount(callback: CallbackQuery, state: FSMContext):
    """Handle skip initial amount button."""
    user_id = callback.from_user.id
    await callback.answer()  # remove loading animation
    await state.update_data(initial_amount=None)
    await callback.message.answer(i18n.get_text('acc_skip_initial_amount', user_id))
    await save_account(callback.message, state)

@router.message(AddAccountState.waiting_for_initial_amount)
async def handle_initial_amount_input(message: Message, state: FSMContext):
    """Handle initial amount input."""
    user_id = message.from_user.id
    try:
        initial_amount_str = message.text.strip().replace(",", ".")
        initial_amount = Decimal(initial_amount_str)
        if initial_amount < 0:
            raise InvalidOperation("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer(i18n.get_text('acc_invalid_amount', user_id))
        return

    await state.update_data(initial_amount=str(initial_amount))
    await message.answer(
        i18n.get_text('acc_initial_amount_saved', user_id, initial_amount=f'{initial_amount:.2f}'),
        parse_mode="Markdown",
    )
    await save_account(message, state)

async def save_account(message: Message, state: FSMContext):
    """Save account to Notion."""
    data = await state.get_data()

    # get user_id properly because message from callback query sometimes misses from_user correctly
    user_id = message.from_user.id if message.from_user else state.key.user_id

    await state.clear()

    try:
        init_amount = data.get("initial_amount")
        account = Account(
            name=data["name"],
            initial_amount=Decimal(init_amount) if init_amount is not None else None,
        )

        success = await notion_writer.add_account(account)

        if success:
            display_amount = f"{account.initial_amount:.2f}" if account.initial_amount is not None else "0.00"
            await message.answer(
                i18n.get_text('acc_saved', user_id, name=account.name, initial_amount=display_amount),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id),
            )
        else:
            await message.answer(
                i18n.get_text('acc_save_failed', user_id),
                reply_markup=await get_main_menu(user_id)
            )

    except Exception as e:
        logger.error(f"Failed to save account: {e}")
        await message.answer(
            i18n.get_text('acc_save_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )

class DeleteAccountsState(StatesGroup):
    """FSM state for accounts."""
    waiting_for_selection = State()

@router.message(F.text.in_(i18n.get_all_translations('btn_del_account')))
async def start_delete_account(message: Message, state: FSMContext):
    """Start logic to delete account in notion db."""
    user_id = message.from_user.id
    await state.clear()
    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer(
            i18n.get_text('acc_no_accounts_to_delete', user_id),
            reply_markup=await get_main_menu(user_id),
        )
        return
    
    await message.answer(
        i18n.get_text('acc_choose_account_delete', user_id),
        parse_mode="Markdown",
        reply_markup=await get_accounts_keyboard(accounts),
    )
    await state.set_state(DeleteAccountsState.waiting_for_selection)

@router.callback_query(F.data.startswith('select_account_'), DeleteAccountsState.waiting_for_selection)
async def process_delete_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection and deletion."""
    user_id = callback.from_user.id
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    await state.clear()
    
    await callback.message.edit_text(i18n.get_text('acc_deleting', user_id), reply_markup=None)

    try:
        success = await notion_writer.delete_page(account_id)
        
        await callback.message.delete() # delete message "Видалення..."

        if success:
            await callback.message.answer(
                i18n.get_text('acc_deleted', user_id),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id),
            )
        else:
            await callback.message.answer(
                i18n.get_text('acc_delete_failed', user_id),
                reply_markup=await get_main_menu(user_id)
            )

    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        await callback.message.answer(
            i18n.get_text('acc_delete_error', user_id),
            reply_markup=await get_main_menu(user_id),
        )