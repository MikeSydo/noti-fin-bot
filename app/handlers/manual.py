import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import any_state
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.keyboards.reply import get_main_menu, get_language_menu
from services.i18n import i18n

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart(), StateFilter(any_state))
async def cmd_start(message: Message, state: FSMContext):
    """Answers for command /start and clears FSM."""
    await state.clear()
    user_id = message.from_user.id

    if i18n.get_user_lang(user_id) is None:
        await message.answer(
            i18n.get_text('msg_start_new_user', lang_code='uk'),
            reply_markup=await get_language_menu()
        )
    else:
        await message.answer(
            i18n.get_text('msg_main_menu', user_id),
            reply_markup=await get_main_menu(user_id)
        )

@router.message(F.text.in_(i18n.get_all_translations('btn_change_language')), StateFilter(any_state))
async def cmd_change_language(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await message.answer(
        i18n.get_text('msg_choose_language', user_id),
        reply_markup=await get_language_menu()
    )

@router.message(F.text.in_(["🇺🇦 Українська", "🇬🇧 English"]), StateFilter(any_state))
async def process_language_selection(message: Message):
    user_id = message.from_user.id
    if message.text == "🇬🇧 English":
        i18n.set_user_lang(user_id, "en")
    else:
        i18n.set_user_lang(user_id, "uk")

    await message.answer(
        i18n.get_text('msg_main_menu', user_id),
        reply_markup=await get_main_menu(user_id)
    )

@router.message(Command('help'), StateFilter(any_state))
async def get_help(message: Message, state: FSMContext):
    """Answers for command /help."""
    user_id = message.from_user.id
    await message.answer(i18n.get_text('msg_help', user_id), parse_mode="Markdown")

@router.message(Command('cancel'), StateFilter(any_state))
@router.message(F.text.in_(i18n.get_all_translations('btn_cancel')), StateFilter(any_state))
async def cmd_cancel(message: Message, state: FSMContext):
    """Allows user to cancel any action."""
    user_id = message.from_user.id
    current_state = await state.get_state()

    logger.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        i18n.get_text('msg_action_cancelled', user_id),
        reply_markup=await get_main_menu(user_id),
    )
