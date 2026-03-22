import logging 

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation
from models.account import Account
from app.keyboards.start_menu import get_main_menu
from services.notion_writer import notion_writer
from app.keyboards.start_menu import get_skip_initial_amount_keyboard
from app.keyboards.start_menu import get_accounts_keyboard

router = Router()

logger = logging.getLogger(__name__)

class AddAccountsState(StatesGroup):
    """FSM state for accounts."""
    waiting_for_name = State()
    waiting_for_initial_amount = State()

@router.message(F.text == 'Додати акаунт')
async def btn_add_account(message: Message, state: FSMContext):
    """Reply keyboard: Add account button."""
    await start_add_account(message, state)

async def start_add_account(message: Message, state: FSMContext):
    """Common logic to add account in notion db."""
    await state.clear()
    await message.answer(
        'Введіть назву акаунта.',
        parse_mode="Markdown",
    )
    await state.set_state(AddAccountsState.waiting_for_name)

@router.message(AddAccountsState.waiting_for_name)
async def handle_account_name_input(message: Message, state: FSMContext):
    """Handle account name input."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    await state.update_data(name=name)
    await message.answer(
        'Назва: {name}\nВведіть початкову суму або натисніть пропустити.'.format(name=name),
        parse_mode="Markdown",
        reply_markup=await get_skip_initial_amount_keyboard(),
    )
    await state.set_state(AddAccountsState.waiting_for_initial_amount)

@router.callback_query(F.data == 'skip_initial_amount', AddAccountsState.waiting_for_initial_amount)
async def handle_skip_initial_amount(callback: CallbackQuery, state: FSMContext):
    """Handle skip initial amount button."""
    await callback.answer()  # remove loading animation
    await state.update_data(initial_amount=None)
    await callback.message.answer('Початкова сума: None')
    await save_account(callback.message, state)

@router.message(AddAccountsState.waiting_for_initial_amount)
async def handle_initial_amount_input(message: Message, state: FSMContext):
    """Handle initial amount input."""
    try:
        initial_amount_str = message.text.strip().replace(",", ".")
        initial_amount = Decimal(initial_amount_str)
        if initial_amount < 0:
            raise InvalidOperation("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer('Некоректна сума. Введіть число, наприклад: 159.90')
        return

    await state.update_data(initial_amount=str(initial_amount))
    await message.answer(
        'Початкова сума: {initial_amount}'.format(initial_amount=f"{initial_amount:.2f}"),
        parse_mode="Markdown",
    )
    await save_account(message, state)

async def save_account(message: Message, state: FSMContext):
    """Save account to Notion."""
    data = await state.get_data()
    await state.clear()

    try:
        init_amount = data.get("initial_amount")
        account = Account(
            name=data["name"],
            initial_amount=Decimal(init_amount) if init_amount is not None else None,
        )

        success = await notion_writer.add_account(account)

        if success:
            await message.answer(
                f"Акаунт збережено!\n\n{account.name}\n{account.initial_amount}",
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

class DeleteAccountsState(StatesGroup):
    """FSM state for accounts."""
    waiting_for_selection = State()

@router.message(F.text == 'Видалити акаунт')
async def btn_delete_account(message: Message, state: FSMContext):
    """Reply keyboard: Delete account button."""
    await start_delete_account(message, state)

async def start_delete_account(message: Message, state: FSMContext):
    """Common logic to delete account in notion db."""
    await state.clear()
    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer(
            'Немає акаунтів для видалення.',
            reply_markup=await get_main_menu(),
        )
        return
    await state.update_data(accounts=accounts)
    await message.answer(
        'Виберіть акаунт для видалення.',
        parse_mode="Markdown",
        reply_markup=await get_accounts_keyboard(accounts),
    )
    await state.set_state(DeleteAccountsState.waiting_for_selection)

@router.callback_query(F.data.startswith('select_account_'), DeleteAccountsState.waiting_for_selection)
async def process_delete_account_selection(callback: CallbackQuery, state: FSMContext):
    """Handle account selection for deletion."""
    await callback.answer()
    account_id = callback.data.replace('select_account_', '')
    await state.update_data(account_id=account_id)
    await callback.message.edit_text("Видалення...", reply_markup=None)
    await delete_account(callback.message, state)

async def delete_account(message: Message, state: FSMContext):
    """Delete account from Notion."""
    data = await state.get_data()
    await state.clear()

    try:
        account_id = data.get("account_id")

        success = await notion_writer.delete_account(account_id)
        
        await message.delete() # delete message "Видалення..."

        if success:
            await message.answer(
                f"Акаунт видалено!",
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