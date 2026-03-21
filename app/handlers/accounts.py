from aiogram import Router, F
from aiogram.types import Message, message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from decimal import Decimal, InvalidOperation

router = Router()

class AddAccountsState(StatesGroup):
    """FSM state for accounts."""
    waiting_for_name = State()
    waiting_for_initial_amount = State()

@router.message(F.text == 'Додати акаунт')
async def btn_add_account(message: Message, state: FSMContext):
    """Reply keyboard: Add account button."""
    await start_add_account(message, state)

async def start_add_account(state: FSMContext):
    """Common logic to add account in notion db."""
    await state.clear()
    await state.set_state(AddAccountsState.waiting_for_name)

@router.callback_query(AddAccountsState.waiting_for_name)
async def handle_add_account_name(state: FSMContext):
    """Handle account name input."""
    name = message.text.strip()
    if not name:
        await message.answer('Назва не може бути порожньою! Дію скасовано.')
        return

    await state.update_data(name=name)
    await message.answer(
        f'Назва: {name}\nВведіть початкову суму або натисніть пропустити.'.format(name=name),
        parse_mode="Markdown",
        #TODO: add func get_skip_name_keyboard()
        #reply_markup=get_skip_name_keyboard(),
    )
    await state.set_state(AddAccountsState.waiting_for_initial_amount)

@router.message(AddAccountsState.waiting_for_initial_amount)
async def handle_name_input(message: Message, state: FSMContext):
    """Handle initial amount input."""
    try:
        initial_amount_str = message.text.strip().replace(",", ".")
        initial_amount = Decimal(initial_amount_str)
        if initial_amount <= 0:
            raise InvalidOperation("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer('Некоректна сума. Введіть число, наприклад: 159.90')
        return

    await state.update_data(initial_amount=str(initial_amount))
    await message.answer(
        f'Початкова сума: {initial_amount}'.format(initial_amount=f"{initial_amount:.2f}"),
        parse_mode="Markdown",
    )
    await state.set_state(AddAccountsState.waiting_for_name)

async def save_account():
    """Save account to Notion."""
    #TODO: need to create service to save data in notion
    pass